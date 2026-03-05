import sys
import socket
import json
import threading
import math
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontDatabase, QPainterPath

# Using a signal to update GUI from the UDP thread safely
class SignalComm(QObject):
    update_mood = pyqtSignal(str, str) # Mood, Optional Text

class DynamicIsland(QWidget):
    def __init__(self):
        super().__init__()
        self.mood = "IDLE" 
        self.text_content = ""
        self.target_width = 200
        self.target_height = 50
        self.current_width = 200
        self.current_height = 50
        self.pulse_val = 0
        
        self.initUI()
        
        # UDP Server for IPC
        self.comm = SignalComm()
        self.comm.update_mood.connect(self.set_mood)
        self.start_udp_server()

        # Animation Loop (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16) 

    def initUI(self):
        # Window Flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initial Geometry (Top Center)
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.center_x = self.screen_width // 2
        
        self.setGeometry(self.center_x - 100, 10, 200, 50)
        self.setWindowTitle('TESS Dynamic Island')
        
        # Label for Text
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #FFA500; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 14px;")
        self.label.hide()
        
        self.show()

    def start_udp_server(self):
        def run_server():
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_socket.bind(('127.0.0.1', 8005))
            print("🏝️ Dynamic Island listening on port 8005...")
            while True:
                try:
                    data, addr = server_socket.recvfrom(1024)
                    msg = json.loads(data.decode())
                    mood = msg.get("mood", "IDLE")
                    text = msg.get("text", "")
                    self.comm.update_mood.emit(mood, text)
                except Exception as e:
                    print(f"UDP Error: {e}")

        threading.Thread(target=run_server, daemon=True).start()

    def set_mood(self, mood, text=""):
        self.mood = mood
        self.text_content = text
        
        # State Machine for Size
        if mood == "IDLE":
            self.target_width = 120
            self.target_height = 35
            self.label.hide()
            
        elif mood == "THINKING":
            self.target_width = 250
            self.target_height = 35
            self.label.setText("Thinking...")
            self.label.show()
            
        elif mood == "BUSY":
            self.target_width = 300
            self.target_height = 35
            self.label.setText(text if text else "Working...")
            self.label.show()
            
        elif mood == "SPEAKING" or mood == "SUCCESS":
            self.target_width = 400
            self.target_height = 80
            self.label.setText(text if text else "Done.")
            self.label.show()
            
        elif mood == "ERROR":
            self.target_width = 300
            self.target_height = 50
            self.label.setText("Error")
            self.label.show()

    def animate(self):
        # Smooth Size Interpolation (Lerp)
        speed = 0.2
        self.current_width += (self.target_width - self.current_width) * speed
        self.current_height += (self.target_height - self.current_height) * speed
        
        # Reposition to keep centered
        new_x = int(self.center_x - (self.current_width / 2))
        self.setGeometry(new_x, 10, int(self.current_width), int(self.current_height))
        
        # Update Label Geometry
        self.label.setGeometry(0, 0, int(self.current_width), int(self.current_height))
        
        # Pulse Logic
        self.pulse_val += 0.1
        
        self.update() # Trigger Paint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        
        # Color Logic
        bg_color = QColor(0, 0, 0, 240) # Deep Black
        border_color = QColor(255, 165, 0) # Orange
        
        if self.mood == "ERROR":
            border_color = QColor(255, 50, 50)
        elif self.mood == "SUCCESS":
            border_color = QColor(50, 255, 50)
            
        # Draw Glow
        painter.setPen(Qt.PenStyle.NoPen)
        # We can implement a glow effect later if needed, mostly handled by border/shadow
        
        # Draw Pill Body
        path = QPainterPath() # Use path via QPainter for rounded rect
        path.addRoundedRect(1, 1, w-2, h-2, h/2, h/2)
        
        painter.setBrush(QBrush(bg_color))
        
        # Subtle pulsing border width
        border_width = 1.5 + (0.5 * math.sin(self.pulse_val)) if self.mood != "IDLE" else 1.0
        painter.setPen(QPen(border_color, border_width))
        
        painter.drawPath(path)
        
        # Scanning Line for Thinking
        if self.mood == "THINKING":
            # Simple scanner line
            scan_x = (math.sin(self.pulse_val * 0.5) + 1) / 2 * (w - 40) + 20
            painter.setPen(QPen(QColor(255, 165, 0, 200), 2))
            painter.drawLine(int(scan_x), int(h/2 - 10), int(scan_x), int(h/2 + 10))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DynamicIsland()
    sys.exit(app.exec())
