import os
import time
import threading
import json
import io
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pyautogui
import mss
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
    JPEG_QUALITY = 50
    FRAME_DELAY = 0.016 # ~60 FPS target (1/60)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            with mss.mss() as sct:
                # Capture the first monitor
                monitor = sct.monitors[1]
                
                try:
                    while True:
                        # High-speed capture
                        start_time = time.time()
                        img = sct.grab(monitor)
                        
                        # Convert to JPEG
                        img_bytes = mss.tools.to_png(img.rgb, img.size) # MSS returns raw pixels
                        # Converting via PIL/Pillow in memory is faster for improvements
                        # But for raw speed, mss -> png bytes is okay, though JPEG is smaller for network
                        
                        # Optimization: Use PIL to convert to JPEG (smaller payload than PNG)
                        import PIL.Image
                        image = PIL.Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                        
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='JPEG', quality=StreamingHandler.JPEG_QUALITY, optimize=True)
                        frame_data = img_byte_arr.getvalue()

                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame_data))
                        self.end_headers()
                        self.wfile.write(frame_data)
                        self.wfile.write(b'\r\n')
                        
                        # Frame pacing
                        elapsed = time.time() - start_time
                        wait = max(0, StreamingHandler.FRAME_DELAY - elapsed)
                        time.sleep(wait)
                        
                except Exception as e:
                    logger.error(f"Stream broken: {e}")
                    pass
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/stop':
            self.send_response(200)
            self.end_headers()
            threading.Thread(target=self.server.shutdown).start()

        elif self.path == '/input':
            content_length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(content_length))
            self.handle_input(data)
            self.send_response(200)
            self.end_headers()

    def handle_input(self, data):
        """Execute remote control actions"""
        try:
            inputType = data.get('type')
            
            if inputType == 'click':
                # Absolute Click (Touch Mode)
                sw, sh = pyautogui.size()
                x, y = int(data['x'] * sw), int(data['y'] * sh)
                pyautogui.click(x, y)
            
            elif inputType == 'key':
                key = data['key']
                # Map special composites
                if key == 'alt+tab':
                    pyautogui.hotkey('alt', 'tab')
                elif key == 'win':
                    pyautogui.press('win')
                elif key == 'space':
                    pyautogui.press('space')
                else:
                    pyautogui.press(key)

            elif inputType == 'text':
                # Smart Type (send full string)
                text = data.get('text', '')
                pyautogui.write(text)

            elif inputType == 'media':
                action = data.get('action')
                if action == 'vol_up': pyautogui.press('volumeup')
                elif action == 'vol_down': pyautogui.press('volumedown')
                elif action == 'mute': pyautogui.press('volumemute')
                elif action == 'play_pause': pyautogui.press('playpause')
                elif action == 'next': pyautogui.press('nexttrack')

        except Exception as e:
            logger.error(f"Input Error: {e}")

    def log_message(self, format, *args):
        return # Silence logs

class ScreencastSkill(BaseSkill):
    """
    Plugin for broadcasting the screen to remote devices.
    V2: Uses mss for high performance and modern UI.
    """
    name = "Screencast"
    intents = ["broadcast_op"]

    def __init__(self, brain=None, port=8000):
        super().__init__(brain)
        self.port = port
        self.server = None
        self.thread = None
        self.is_running = False

    def execute(self, action_data: dict, context: dict) -> str:
        sub_action = action_data.get("sub_action", "start")
        if sub_action == "start": return self.start()
        elif sub_action == "stop": return self.stop()
        return f"Unknown broadcast action: {sub_action}"

    def find_available_port(self, start_port):
        port = start_port
        while port < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
                port += 1
        return start_port

    def start(self):
        if self.is_running:
            return f"Screencast V2 running at {self.get_ip()}:{self.port}"
        
        try:
            self.port = self.find_available_port(self.port)
            self.server = ThreadingHTTPServer(('0.0.0.0', self.port), StreamingHandler)
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            self.is_running = True
            
            ip = self.get_ip()
            url = f"http://{ip}:{self.port}"
            return f"🚀 Screencast V2 Started! FAST & MODERN.\nOpen {url} on your phone."
        except Exception as e:
            logger.error(f"Screencast Start Error: {e}", exc_info=True)
            self.is_running = False
            return f"Failed to start broadcast: {e}"

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
            finally:
                self.server = None
                self.is_running = False
            return "Broadcast stopped."
        return "No broadcast running."

    def get_ip(self):
        """
        Detects the best local IP for broadcasting.
        Prioritizes:
        1. 10.68.248.139 (User requested)
        2. 192.168.x.x (Standard System LAN)
        3. 10.x.x.x (Enterprise/VPN LAN)
        4. Standard socket detection (8.8.8.8)
        """
        try:
            import psutil
            
            # 1. Gather all IPv4 addresses
            ips = []
            for interface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET:
                        ips.append(snic.address)
            
            # 2. User Explicit Override (Bind is 0.0.0.0 so this is safe for display)
            return "10.68.248.139"

            # 3. Check for 10.* (User preferred)
            for ip in ips:
                if ip.startswith("10."):
                    return ip

            # 4. Check for Standard LAN (192.168.*)
            for ip in ips:
                if ip.startswith("192.168."):
                    return ip

            # 5. Fallback to old method (outbound connection)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
            
        except Exception as e:
            logger.error(f"Error resolving IP: {e}")
            return "127.0.0.1"
