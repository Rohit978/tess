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
# HTML Template with Remote Control Logic
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>TESS Remote Desktop</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <style>
        body, html { margin: 0; padding: 0; background: #000; height: 100%; overflow: hidden; touch-action: none; font-family: sans-serif; }
        #stream { width: 100%; height: 100%; object-fit: contain; cursor: crosshair; }
        
        /* Floating Dock */
        #dock {
            position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
            display: flex; gap: 15px; align-items: center;
            background: rgba(20, 20, 20, 0.85);
            padding: 10px 20px; border-radius: 20px;
            border: 1px solid rgba(0, 255, 255, 0.3);
            backdrop-filter: blur(10px);
            opacity: 0.4; transition: opacity 0.3s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        #dock:hover { opacity: 1.0; }
        
        .btn {
            background: none; border: none; font-size: 24px; cursor: pointer;
            transition: transform 0.2s; padding: 5px;
            filter: grayscale(1);
        }
        .btn:hover { transform: scale(1.2); filter: grayscale(0); }
        .btn:active { transform: scale(0.9); }
        
        /* Status Dot */
        #status {
            width: 10px; height: 10px; border-radius: 50%;
            background: #00ff00; box-shadow: 0 0 10px #00ff00;
            animation: pulse 2s infinite;
        }
        
        /* Quality Slider */
        .slider-cont { display: flex; flex-direction: column; align-items: center; gap: 2px; }
        input[type=range] { width: 80px; accent-color: cyan; }
        .label { font-size: 10px; color: #aaa; text-transform: uppercase; }

        @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
        
        #kbd-input { position: absolute; opacity: 0; top: -1000px; }
    </style>
</head>
<body>
    <img id="stream" src="/stream.mjpg" draging="false" />
    
    <div id="dock">
        <div id="status" title="Live"></div>
        
        <button class="btn" onclick="toggleKeyboard()" title="Keyboard">⌨️</button>
        <button class="btn" id="touch-btn" onclick="toggleTouchMode()" title="Toggle Touch Mode">👆</button>
        
        <div class="slider-cont">
            <span class="label">Quality</span>
            <input type="range" min="10" max="80" value="40" onchange="setQuality(this.value)">
        </div>
        
        <button class="btn" onclick="stopShare()" title="Stop Sharing" style="filter: none;">🛑</button>
    </div>
    
    <input type="text" id="kbd-input" oninput="handleTyping(this)">

    <script>
        const img = document.getElementById('stream');
        const container = document.body;
        
        // State
        let scale = 1;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let startX, startY;
        
        // Touch Mode State
        let isTouchMode = false;
        let touchStartY = 0;
        let touchStartX = 0;
        let isScrolling = false;

        function toggleTouchMode() {
            isTouchMode = !isTouchMode;
            const btn = document.getElementById('touch-btn');
            btn.style.filter = isTouchMode ? 'none' : 'grayscale(1)';
            btn.style.transform = isTouchMode ? 'scale(1.1)' : 'scale(1)';
            // Visual feedback
            const status = document.getElementById('status');
            status.style.background = isTouchMode ? 'cyan' : '#00ff00';
            status.style.boxShadow = isTouchMode ? '0 0 10px cyan' : '0 0 10px #00ff00';
        }

        // --- ZOOM & PAN (Desktop/Mobile) ---
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = -Math.sign(e.deltaY) * 0.1;
            const newScale = Math.max(1, Math.min(5, scale + delta));
            scale = newScale;
            updateTransform();
        }, {passive: false});

        // Pointer Handling (Unified for Mouse/Touch)
        container.addEventListener('pointerdown', (e) => {
            // If interacting with dock or controls, ignore
            if (e.target.closest('#dock') || e.target.closest('#kbd-input')) return;

            if (scale > 1) {
                 // Pan Logic when Zoomed
                 isDragging = true;
                 startX = e.clientX - panX;
                 startY = e.clientY - panY;
            } else if (isTouchMode) {
                 // Touch Mode: Prepare for Scroll or Tap
                 isScrolling = true;
                 touchStartY = e.clientY;
                 touchStartX = e.clientX;
            } else {
                 // Mouse Mode: Direct Click (handled by img listener mostly, but let's be explicitly safe)
            }
        });
        
        container.addEventListener('pointermove', (e) => {
            if (isDragging && scale > 1) {
                e.preventDefault();
                panX = e.clientX - startX;
                panY = e.clientY - startY;
                updateTransform();
                return;
            }
            
            if (isScrolling && isTouchMode && scale === 1) {
                // Scroll Logic
                e.preventDefault();
                const dy = e.clientY - touchStartY;
                // Threshold to avoid accidental micro-scrolls on taps
                if (Math.abs(dy) > 5) {
                    sendInput('scroll', {dy: dy / 10}); // Divider to tame speed
                    touchStartY = e.clientY; // Reset for continuous delta
                }
            }
        });
        
        container.addEventListener('pointerup', (e) => {
            isDragging = false;
            
            if (isScrolling && isTouchMode && scale === 1) {
                isScrolling = false;
                // Check if it was a Tap (minimal movement)
                const dist = Math.hypot(e.clientX - touchStartX, e.clientY - touchStartY);
                if (dist < 10) {
                    // It's a TAP -> Click
                    sendInput('click', getCoords(e));
                }
            }
        });

        function updateTransform() {
            img.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        }

        // --- MOUSE MODE INPUT (Legacy/Precision) ---
        img.addEventListener('pointerdown', (e) => {
            if(!isTouchMode && scale === 1) sendInput('mousedown', getCoords(e));
        });
        img.addEventListener('pointerup', (e) => {
             if(!isTouchMode && scale === 1) sendInput('mouseup', getCoords(e));
        });
        
        function getCoords(e) {
            const rect = img.getBoundingClientRect();
            const rw = rect.width; 
            const rh = rect.height;
            const safeX = (e.clientX - rect.left) / rw;
            const safeY = (e.clientY - rect.top) / rh;
            return {x: Math.max(0, Math.min(1, safeX)), y: Math.max(0, Math.min(1, safeY))};
        }

        // --- CONTROLS ---
        function toggleKeyboard() { document.getElementById('kbd-input').focus(); }
        
        function handleTyping(el) {
            if (el.value.length > 0) {
                sendInput('type', {key: el.value[el.value.length - 1]});
                el.value = ""; 
            }
        }
        
        function setQuality(val) {
            fetch('/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({quality: parseInt(val)})
            });
        }
        
        function stopShare() {
            if(confirm("Stop sharing screen?")) {
                fetch('/stop', {method: 'POST'}).then(() => {
                    document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:20%'>Broadcast Stopped 👋</h1>";
                });
            }
        }

        function sendInput(type, data) {
            fetch('/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type, ...data})
            });
        }
    </script>
</body>
</html>
"""

class StreamingHandler(BaseHTTPRequestHandler):
    JPEG_QUALITY = 40
    FRAME_DELAY = 0.04 # ~25 FPS

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
                    screenshot = pyautogui.screenshot()
                    img_byte_arr = io.BytesIO()
                    # Dynamic Quality
                    screenshot.save(img_byte_arr, format='JPEG', quality=StreamingHandler.JPEG_QUALITY)
                    frame_data = img_byte_arr.getvalue()

                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame_data))
                    self.end_headers()
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
                    
                    time.sleep(StreamingHandler.FRAME_DELAY)
            except Exception:
                pass
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/settings':
            content_length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(content_length))
            
            if 'quality' in data:
                StreamingHandler.JPEG_QUALITY = max(10, min(90, data['quality']))
            
            self.send_response(200)
            self.end_headers()

        elif self.path == '/stop':
            self.send_response(200)
            self.end_headers()
            # Shut down server in separate thread to avoid deadlock
            threading.Thread(target=self.server.shutdown).start()

        elif self.path == '/input':
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
            if data['type'] in ['mousedown', 'mouseup', 'click']:
                # Defensive checks for coordinates
                raw_x = data.get('x')
                raw_y = data.get('y')
                
                if raw_x is None or raw_y is None:
                    # Logic might send events without coords in some edge cases
                    return

                x = int(raw_x * screen_w)
                y = int(raw_y * screen_h)
                
                if data['type'] == 'mousedown':
                    pyautogui.mouseDown(x, y)
                elif data['type'] == 'mouseup':
                    pyautogui.mouseUp(x, y)
                else:
                    pyautogui.click(x, y)
                
            elif data['type'] == 'type':
                key = data['key']
                if key == "enter": pyautogui.press('enter')
                elif key == "backspace": pyautogui.press('backspace')
                else: pyautogui.write(key)
            
            elif data['type'] == 'scroll':
                # dy is vertical scroll amount
                dy = int(data.get('dy', 0))
                if dy != 0:
                    pyautogui.scroll(dy * 50) # Multiplier for sensitivity
                
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
