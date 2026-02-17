import os
import time
import threading
import json
import io
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pyautogui
from ..core.logger import setup_logger

logger = setup_logger("Screencast")

# HTML Template with Remote Control Logic
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>TESS Remote Desktop</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body, html { margin: 0; padding: 0; background: #000; height: 100%; overflow: hidden; }
        #stream { width: 100%; height: 100%; object-fit: contain; cursor: crosshair; }
        #controls { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; }
        .btn { padding: 10px 20px; background: rgba(0, 255, 255, 0.5); color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; }
        .btn:active { background: rgba(0, 255, 255, 0.8); }
        #kbd-input { position: absolute; opacity: 0; top: -1000px; }
    </style>
</head>
<body>
    <img id="stream" src="/stream.mjpg" />
    
    <div id="controls">
        <button class="btn" onclick="toggleKeyboard()">⌨️ Keyboard</button>
        <button class="btn" onclick="sendKey('backspace')">⌫</button>
        <button class="btn" onclick="sendKey('enter')">⏎</button>
        <button class="btn" onclick="location.reload()">🔄 Reload</button>
    </div>
    
    <input type="text" id="kbd-input" oninput="handleTyping(this)">

    <script>
        const img = document.getElementById('stream');
        
        // --- MOUSE CONTROL ---
        img.addEventListener('click', (e) => {
            sendInput('click', getCoords(e));
        });

        // Optional: Drag support (simplified as click for now to save bandwidth)
        
        function getCoords(e) {
            const rect = img.getBoundingClientRect();
            // Calculate relative coordinates (0.0 to 1.0) based on the image display size
            // This handles generic scaling ("object-fit: contain")
            
            // Note: This is an approximation. For pixel-perfect mapping with object-fit, 
            // we'd need to calculate the actual rendered image dimensions. 
            // For now, we map to the element, which works well if it fills screen.
            
            let x = (e.clientX - rect.left) / rect.width;
            let y = (e.clientY - rect.top) / rect.height;
            return {x, y};
        }

        // --- KEYBOARD CONTROL ---
        function toggleKeyboard() {
            const inp = document.getElementById('kbd-input');
            inp.focus();
            inp.click();
        }

        function handleTyping(el) {
            if (el.value.length > 0) {
                const char = el.value[el.value.length - 1];
                sendKey(char);
                el.value = ""; // Clear
            }
        }

        function sendKey(key) {
            fetch('/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type: 'type', key: key})
            });
        }

        function sendInput(type, data) {
            fetch('/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type: type, ...data})
            });
        }
    </script>
</body>
</html>
"""

class StreamingHandler(BaseHTTPRequestHandler):
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
            try:
                while True:
                    # Capture Screen
                    screenshot = pyautogui.screenshot()
                    # Resize for performance (optional, keeping full res for clarity but adjusting quality)
                    # screenshot.thumbnail((1280, 720)) 
                    
                    img_byte_arr = io.BytesIO()
                    screenshot.save(img_byte_arr, format='JPEG', quality=50) # Lower quality for speed
                    frame_data = img_byte_arr.getvalue()

                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame_data))
                    self.end_headers()
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
                    
                    time.sleep(0.05) # ~20 FPS cap
            except Exception as e:
                pass
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/input':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            self.handle_input(data)
            
            self.send_response(200)
            self.end_headers()

    def handle_input(self, data):
        """Execute remote control actions"""
        screen_w, screen_h = pyautogui.size()
        
        try:
            if data['type'] == 'click':
                # Convert relative (0-1) to absolute pixels
                x = int(data['x'] * screen_w)
                y = int(data['y'] * screen_h)
                pyautogui.click(x, y)
                
            elif data['type'] == 'type':
                key = data['key']
                # Special mapping or direct pass
                if key == "enter": pyautogui.press('enter')
                elif key == "backspace": pyautogui.press('backspace')
                else: pyautogui.write(key)
                
        except Exception as e:
            logger.error(f"Input Error: {e}")
    
    def log_message(self, format, *args):
        return # Silence server logs

class ScreencastSkill:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.thread = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return f"Screencast already running at {self.get_ip()}:{self.port}"
        
        try:
            self.server = ThreadingHTTPServer(('0.0.0.0', self.port), StreamingHandler)
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            self.is_running = True
            
            url = f"http://{self.get_ip()}:{self.port}"
            return f"🚀 Broadcast started! Open {url} on your phone."
        except Exception as e:
            return f"Failed to start broadcast: {e}"

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.is_running = False
            return "Broadcast stopped."
        return "No broadcast running."

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
