import io
import json
import os
import socket
import subprocess
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

RULE_NAME_PREFIX = "TESS Screencast Port"

# Load UI from file
UI_PATH = os.path.join(os.path.dirname(__file__), "screencast_ui.html")
try:
    with open(UI_PATH, "r", encoding="utf-8") as f:
        HTML_PAGE = f.read()
except Exception as e:
    logger.error(f"Failed to load UI template: {e}")
    HTML_PAGE = "<h1>Error loading UI</h1>"

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TARGET_FPS      = 30
FRAME_BUDGET    = 1.0 / TARGET_FPS          # 33.33 ms per frame
JPEG_QUALITY    = 60                        # balanced quality / speed
MAX_WIDTH       = 1280                      # downscale if screen is wider
MAX_HEIGHT      = 800                       # downscale if screen is taller


def _resize_if_needed(image: "Image.Image") -> "Image.Image":
    """Downscale image proportionally if it exceeds MAX dimensions."""
    w, h = image.size
    if w <= MAX_WIDTH and h <= MAX_HEIGHT:
        return image
    ratio = min(MAX_WIDTH / w, MAX_HEIGHT / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    return image.resize((new_w, new_h), Image.BILINEAR)


class StreamingHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self._serve_html()
        elif self.path == "/health":
            self._serve_json(b'{"status":"ok"}')
        elif self.path == "/stream.mjpg":
            self._serve_stream()
        else:
            self.send_error(404)

    # ── Helpers ───────────────────────────────
    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def _serve_json(self, payload: bytes):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

        running_event = getattr(self.server, "running_event", None)

        with mss.mss() as sct:
            monitors = sct.monitors
            # monitors[0] is the "all monitors" virtual screen; monitors[1] is primary
            monitor = monitors[1] if len(monitors) > 1 else monitors[0]

            while True:
                if running_event is not None and not running_event.is_set():
                    break

                frame_start = time.perf_counter()

                try:
                    if Image is None:
                        raise RuntimeError(
                            "Pillow is required for MJPEG encoding but is not installed."
                        )

                    # ── Capture ─────────────────────────────
                    raw = sct.grab(monitor)
                    image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

                    # ── Downscale ───────────────────────────
                    image = _resize_if_needed(image)

                    # ── Encode ──────────────────────────────
                    buf = io.BytesIO()
                    image.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=False)
                    frame_data = buf.getvalue()

                    # ── Send ────────────────────────────────
                    header = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame_data)}\r\n\r\n".encode()
                    )
                    self.wfile.write(header)
                    self.wfile.write(frame_data)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()

                except (BrokenPipeError, ConnectionResetError):
                    break
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    break

                # ── Deadline-aware pacing ────────────────
                elapsed = time.perf_counter() - frame_start
                sleep_time = FRAME_BUDGET - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # If over budget, skip sleep and push next frame immediately

    # ── POST ──────────────────────────────────
    def do_POST(self):
        if self.path == "/stop":
            self.send_response(200)
            self.end_headers()
            running_event = getattr(self.server, "running_event", None)
            if running_event:
                running_event.clear()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if self.path == "/input":
            self._handle_input_request()
            return

        self.send_error(404)

    def _handle_input_request(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw) if raw else {}
            self._dispatch_input(data)
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logger.error(f"Input request error: {e}")
            self.send_response(400)
            self.end_headers()

    def _dispatch_input(self, data: dict):
        """Route input events to pyautogui actions."""
        try:
            itype = data.get("type")
            sw, sh = pyautogui.size()

            if itype == "click":
                btn = data.get("button", "left")
                x = max(0, min(sw - 1, int(float(data.get("x", 0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0)) * sh)))
                pyautogui.click(x, y, button=btn)

            elif itype == "rightclick":
                x = max(0, min(sw - 1, int(float(data.get("x", 0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0)) * sh)))
                pyautogui.rightClick(x, y)

            elif itype == "move":
                x = max(0, min(sw - 1, int(float(data.get("x", 0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0)) * sh)))
                pyautogui.moveTo(x, y, _pause=False)

            elif itype == "drag":
                x = max(0, min(sw - 1, int(float(data.get("x", 0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0)) * sh)))
                pyautogui.dragTo(x, y, button="left", _pause=False)

            elif itype == "scroll":
                x = max(0, min(sw - 1, int(float(data.get("x", 0)) * sw)))
                y = max(0, min(sh - 1, int(float(data.get("y", 0)) * sh)))
                clicks = int(data.get("delta", 0))
                pyautogui.scroll(clicks, x=x, y=y)

            elif itype == "key":
                key = str(data.get("key", "")).strip().lower()
                if not key:
                    return
                if "+" in key:
                    parts = key.split("+")
                    pyautogui.hotkey(*parts)
                else:
                    pyautogui.press(key)

            elif itype == "text":
                text = str(data.get("text", ""))
                if text:
                    pyautogui.write(text, interval=0.02)

            elif itype == "media":
                action_map = {
                    "vol_up":    "volumeup",
                    "vol_down":  "volumedown",
                    "mute":      "volumemute",
                    "play_pause":"playpause",
                    "next":      "nexttrack",
                    "prev":      "prevtrack",
                }
                key = action_map.get(data.get("action", ""))
                if key:
                    pyautogui.press(key)

        except Exception as e:
            logger.error(f"Input dispatch error: {e}")

    def log_message(self, _format, *_args):
        return  # suppress request logs


# ──────────────────────────────────────────────
# Skill Class
# ──────────────────────────────────────────────
class ScreencastSkill(BaseSkill):
    """
    Plugin for broadcasting the screen to remote devices via MJPEG.

    Lifecycle guarantees:
    - Port probing via bind test before binding
    - Idempotent start/stop (safe to call multiple times)
    - Consistent IP selection with LAN-priority ordering
    - Deadline-aware 30 FPS frame pacing
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
        self._tunnel_url: str | None = None          # public internet URL
        self._cf_proc = None                          # cloudflared subprocess (if used)

    # ── Entry Point ───────────────────────────
    def execute(self, action_data: dict, context: dict) -> str:
        sub = str(action_data.get("sub_action", "start")).strip().lower()
        if sub == "start":
            return self.start()
        if sub == "stop":
            return self.stop()
        if sub == "status":
            return self.status()
        return f"Unknown broadcast action: '{sub}'. Use start, stop, or status."

    # ── Lifecycle ─────────────────────────────
    # ── Tunnel helpers ────────────────────────
    def _start_tunnel(self) -> str | None:
        """
        Expose the local HTTP server to the public internet.
        Tries ngrok first, then cloudflared quick-tunnel.
        Returns the public URL string, or None if both fail.
        """
        # ── 1. ngrok via pyngrok ──────────────
        try:
            from pyngrok import ngrok, conf as ngrok_conf
            # Suppress pyngrok's own logging
            import logging as _logging
            _logging.getLogger("pyngrok").setLevel(_logging.WARNING)
            tunnel = ngrok.connect(self.port, "http")
            url = tunnel.public_url.replace("http://", "https://")
            logger.info(f"ngrok tunnel active: {url}")
            return url
        except Exception as e:
            logger.warning(f"ngrok unavailable ({e}), trying cloudflared…")

        # ── 2. cloudflared quick-tunnel ───────
        try:
            import re as _re
            proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{self.port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self._cf_proc = proc
            # cloudflared prints the URL to stdout/stderr; wait up to 8 s
            deadline = time.time() + 8
            while time.time() < deadline:
                line = proc.stdout.readline()
                m = _re.search(r"https://[\w.-]+\.trycloudflare\.com", line)
                if m:
                    url = m.group(0)
                    logger.info(f"cloudflared tunnel active: {url}")
                    return url
        except FileNotFoundError:
            logger.warning("cloudflared binary not found; tunnel unavailable.")
        except Exception as e:
            logger.warning(f"cloudflared failed: {e}")

        return None

    def _stop_tunnel(self):
        """Shut down whichever tunnel was started."""
        # ngrok
        try:
            from pyngrok import ngrok
            ngrok.kill()
        except Exception:
            pass
        # cloudflared
        if self._cf_proc:
            try:
                self._cf_proc.terminate()
            except Exception:
                pass
            self._cf_proc = None
        self._tunnel_url = None

    # ── Firewall helpers ──────────────────────
    def _fw_rule_name(self) -> str:
        return f"TESS Screencast Port {self.port}"

    def _open_firewall(self):
        """Add an inbound firewall rule so LAN devices can reach the stream."""
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name={self._fw_rule_name()}",
                    "dir=in", "action=allow", "protocol=TCP",
                    f"localport={self.port}",
                    "profile=any",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            logger.info(f"Firewall rule added for port {self.port}")
        except Exception as e:
            logger.warning(f"Could not add firewall rule (run as admin for LAN access): {e}")

    def _close_firewall(self):
        """Remove the inbound firewall rule created on start."""
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f"name={self._fw_rule_name()}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            logger.info(f"Firewall rule removed for port {self.port}")
        except Exception as e:
            logger.warning(f"Could not remove firewall rule: {e}")

    def start(self) -> str:
        with self._lifecycle_lock:
            if self._is_alive():
                return f"Screencast already running at {self._server_url()}"

            # Reset stale state from a crash
            self.server = None
            self.thread = None
            self.is_running = False

            try:
                self.port = self.find_available_port(self.port or self.default_port)
                self.running_event.set()

                self.server = ThreadingHTTPServer(("0.0.0.0", self.port), StreamingHandler)
                self.server.daemon_threads = True
                self.server.running_event = self.running_event

                self.thread = threading.Thread(
                    target=self.server.serve_forever, daemon=True, name="ScreencastServer"
                )
                self.thread.start()

                # Brief settler — confirm thread actually started
                time.sleep(0.15)
                if not self.thread.is_alive():
                    raise RuntimeError("Broadcast thread failed to start.")

                # Open firewall so LAN devices can connect
                self._open_firewall()

                # Create public internet tunnel
                self._tunnel_url = self._start_tunnel()

                self.is_running = True
                local_url = self._server_url()
                msg = f"Screencast started at {TARGET_FPS} FPS.\n"
                msg += f"  LAN  : {local_url}\n"
                if self._tunnel_url:
                    msg += f"  Internet: {self._tunnel_url}"
                else:
                    msg += "  Internet tunnel unavailable (install ngrok or cloudflared)."
                return msg
            except Exception as e:
                logger.error(f"Screencast Start Error: {e}", exc_info=True)
                self._teardown()
                return f"Failed to start broadcast: {e}"

    def stop(self) -> str:
        with self._lifecycle_lock:
            if not self._is_alive() and not self.is_running:
                return "No broadcast running."
            self._teardown()
            return "Broadcast stopped."

    def _teardown(self):
        """Internal: shut down server, tunnel, firewall rule, and reset all state."""
        self.running_event.clear()
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
        except Exception as e:
            logger.error(f"Error during server teardown: {e}")
        finally:
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=3)
            self.server = None
            self.thread = None
            self.is_running = False
        self._stop_tunnel()
        self._close_firewall()

    def status(self) -> str:
        if self._is_alive():
            msg = f"Broadcast running @ {TARGET_FPS} FPS\n"
            msg += f"  LAN     : {self._server_url()}\n"
            if self._tunnel_url:
                msg += f"  Internet: {self._tunnel_url}"
            else:
                msg += "  Internet: no tunnel active"
            return msg
        return "Broadcast is not running."

    # ── Helpers ───────────────────────────────
    def _is_alive(self) -> bool:
        return bool(self.server and self.thread and self.thread.is_alive() and self.is_running)

    def _server_url(self) -> str:
        return f"http://{self.get_ip()}:{self.port}"

    def _is_port_free(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return True
        except OSError:
            return False

    def find_available_port(self, start_port: int) -> int:
        port = int(start_port)
        while port < 65535:
            if self._is_port_free(port):
                return port
            port += 1
        return self.default_port

    def get_ip(self) -> str:
        """
        Detect best local IPv4 for LAN broadcasting.
        Priority order: 192.168.x.x → 10.x.x.x → 172.16-31.x.x → any → localhost
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

            for prefix in ("192.168.", "10."):
                for ip in candidates:
                    if ip.startswith(prefix):
                        return ip

            for ip in candidates:
                if ip.startswith("172."):
                    try:
                        if 16 <= int(ip.split(".")[1]) <= 31:
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
