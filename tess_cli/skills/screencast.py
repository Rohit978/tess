import io
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mss
import pyautogui
try:
    from PIL import Image
except Exception:
    Image = None

from ..core.logger import setup_logger
from .base_skill import BaseSkill

logger = setup_logger("Screencast")

# Load UI from file
UI_PATH = os.path.join(os.path.dirname(__file__), "screencast_ui.html")
try:
    with open(UI_PATH, "r", encoding="utf-8") as f:
        HTML_PAGE = f.read()
except Exception as e:
    logger.error(f"Failed to load UI template: {e}")
    HTML_PAGE = "<h1>Error loading UI</h1>"


class StreamingHandler(BaseHTTPRequestHandler):
    JPEG_QUALITY = 55
    FRAME_DELAY = 0.033  # ~30 FPS target

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        if self.path != "/stream.mjpg":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

        running_event = getattr(self.server, "running_event", None)
        with mss.mss() as sct:
            monitors = sct.monitors
            monitor = monitors[1] if len(monitors) > 1 else monitors[0]

            while True:
                if running_event is not None and not running_event.is_set():
                    break

                start_time = time.time()
                try:
                    if Image is None:
                        raise RuntimeError("Pillow is required for MJPEG encoding but is not available.")
                    img = sct.grab(monitor)
                    image = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format="JPEG", quality=self.JPEG_QUALITY, optimize=True)
                    frame_data = img_byte_arr.getvalue()

                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame_data)}\r\n\r\n".encode("utf-8"))
                    self.wfile.write(frame_data)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    break

                elapsed = time.time() - start_time
                wait = max(0, self.FRAME_DELAY - elapsed)
                time.sleep(wait)

    def do_POST(self):
        if self.path == "/stop":
            self.send_response(200)
            self.end_headers()
            running_event = getattr(self.server, "running_event", None)
            if running_event:
                running_event.clear()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if self.path != "/input":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            data = json.loads(raw) if raw else {}
            self.handle_input(data)
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logger.error(f"Input request error: {e}")
            self.send_response(400)
            self.end_headers()

    def handle_input(self, data):
        """Execute remote control actions."""
        try:
            input_type = data.get("type")

            if input_type == "click":
                sw, sh = pyautogui.size()
                x = max(0, min(sw - 1, int(float(data.get("x", 0.0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0.0)) * sh)))
                pyautogui.click(x, y)
                return

            if input_type == "key":
                key = str(data.get("key", "")).strip().lower()
                if not key:
                    return
                if key == "alt+tab":
                    pyautogui.hotkey("alt", "tab")
                elif key == "win":
                    pyautogui.press("win")
                elif key == "space":
                    pyautogui.press("space")
                else:
                    pyautogui.press(key)
                return

            if input_type == "text":
                text = str(data.get("text", ""))
                if text:
                    pyautogui.write(text)
                return

            if input_type == "media":
                action = data.get("action")
                if action == "vol_up":
                    pyautogui.press("volumeup")
                elif action == "vol_down":
                    pyautogui.press("volumedown")
                elif action == "mute":
                    pyautogui.press("volumemute")
                elif action == "play_pause":
                    pyautogui.press("playpause")
                elif action == "next":
                    pyautogui.press("nexttrack")
        except Exception as e:
            logger.error(f"Input Error: {e}")

    def log_message(self, _format, *_args):
        return


class ScreencastSkill(BaseSkill):
    """
    Plugin for broadcasting the screen to remote devices.
    Hardened lifecycle:
    - Port probing via bind test
    - Idempotent start/stop
    - Consistent IP selection and server status checks
    """

    name = "Screencast"
    intents = ["broadcast_op"]

    def __init__(self, brain=None, port=8000):
        super().__init__(brain)
        self.default_port = int(port)
        self.port = int(port)
        self.server = None
        self.thread = None
        self.is_running = False
        self.running_event = threading.Event()
        self._lifecycle_lock = threading.Lock()

    def execute(self, action_data: dict, context: dict) -> str:
        sub_action = str(action_data.get("sub_action", "start")).strip().lower()
        if sub_action == "start":
            return self.start()
        if sub_action == "stop":
            return self.stop()
        if sub_action == "status":
            return self.status()
        return f"Unknown broadcast action: {sub_action}. Use start, stop, or status."

    def _is_port_free(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
                return True
        except OSError:
            return False

    def find_available_port(self, start_port):
        port = int(start_port)
        while port < 65535:
            if self._is_port_free(port):
                return port
            port += 1
        return self.default_port

    def _is_alive(self):
        return bool(self.server and self.thread and self.thread.is_alive() and self.is_running)

    def _server_url(self):
        return f"http://{self.get_ip()}:{self.port}"

    def start(self):
        with self._lifecycle_lock:
            if self._is_alive():
                return f"Screencast running at {self._server_url()}"

            # Clean stale references if previous run died unexpectedly.
            self.server = None
            self.thread = None
            self.is_running = False

            try:
                self.port = self.find_available_port(self.port or self.default_port)
                self.running_event.set()
                self.server = ThreadingHTTPServer(("0.0.0.0", self.port), StreamingHandler)
                self.server.daemon_threads = True
                self.server.running_event = self.running_event

                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()

                # Confirm thread has started.
                time.sleep(0.1)
                if not self.thread.is_alive():
                    raise RuntimeError("Broadcast thread failed to start.")

                self.is_running = True
                url = self._server_url()
                return f"Screencast started.\nOpen {url} on your phone."
            except Exception as e:
                logger.error(f"Screencast Start Error: {e}", exc_info=True)
                self.running_event.clear()
                self.is_running = False
                try:
                    if self.server:
                        self.server.server_close()
                except Exception:
                    pass
                self.server = None
                self.thread = None
                return f"Failed to start broadcast: {e}"

    def stop(self):
        with self._lifecycle_lock:
            if not self.server and not self.thread and not self.is_running:
                return "No broadcast running."

            self.running_event.clear()
            try:
                if self.server:
                    self.server.shutdown()
                    self.server.server_close()
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
            finally:
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=2)
                self.server = None
                self.thread = None
                self.is_running = False
            return "Broadcast stopped."

    def status(self):
        if self._is_alive():
            return f"Broadcast is running at {self._server_url()}"
        return "Broadcast is not running."

    def get_ip(self):
        """
        Detect the best local IPv4 for LAN broadcasting.
        Priority:
        1. 192.168.x.x
        2. 10.x.x.x
        3. 172.16-31.x.x
        4. outbound socket detection
        5. localhost fallback
        """
        try:
            import psutil

            candidates = []
            for _iface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family != socket.AF_INET:
                        continue
                    ip = snic.address
                    if not ip or ip.startswith("127.") or ip.startswith("169.254."):
                        continue
                    candidates.append(ip)

            for ip in candidates:
                if ip.startswith("192.168."):
                    return ip
            for ip in candidates:
                if ip.startswith("10."):
                    return ip
            for ip in candidates:
                if ip.startswith("172."):
                    try:
                        second_octet = int(ip.split(".")[1])
                        if 16 <= second_octet <= 31:
                            return ip
                    except Exception:
                        continue

            if candidates:
                return candidates[0]
        except Exception as e:
            logger.error(f"IP discovery via interfaces failed: {e}")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception as e:
            logger.error(f"IP fallback resolution failed: {e}")
            return "127.0.0.1"
