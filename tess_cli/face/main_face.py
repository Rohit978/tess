import sys
import socket
import json
import threading
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush

# Using a signal to update GUI from the UDP thread safely
class SignalComm(QObject):
    update_mood = pyqtSignal(str)

class TessFace(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.mood = "IDLE" 
        self.animation_frame = 0
        
        # UDP Server for IPC
        self.comm = SignalComm()
        self.comm.update_mood.connect(self.set_mood)
        self.start_udp_server()

        # Animation Loop (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16) 

    def initUI(self):
        # Transparent, Always on Top, Frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Full Screen Overlay (Click-through)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        
        # Make click-through (ignore mouse events)
        # On Windows, we might need Win32 calls for true click-through, 
        # but Qt.WindowTransparentForInput works if supported by OS compositor.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setWindowTitle('TESS Eyes')
        self.show()

    def start_udp_server(self):
        def run_server():
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_socket.bind(('127.0.0.1', 8005))
            print("👁️ TESS Face listening on port 8005...")
            while True:
                try:
                    data, addr = server_socket.recvfrom(1024)
                    msg = json.loads(data.decode())
                    if "mood" in msg:
                        self.comm.update_mood.emit(msg["mood"])
                except Exception as e:
                    print(f"UDP Error: {e}")

        threading.Thread(target=run_server, daemon=True).start()

    def set_mood(self, mood):
        self.mood = mood
        self.animation_frame = 0 # Reset animation on mood switch
        self.update()

    def animate(self):
        self.animation_frame += 1
        self.update() # Trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Eyes
        w, h = self.width(), self.height()
        eye_spacing = 300
        
        self.draw_eye(painter, w/2 - eye_spacing/2, h/3) # Left
        self.draw_eye(painter, w/2 + eye_spacing/2, h/3) # Right

    def draw_eye(self, painter, x, y):
        # Style Config based on Mood
        color = QColor(0, 255, 255) # Default Cyan
        size_mult = 1.0
        
        if self.mood == "THINKING":
            color = QColor(0, 150, 255) # Deep Blue
            # Pulsing effect
            import math
            size_mult = 1.0 + 0.1 * math.sin(self.animation_frame * 0.2)
            
        elif self.mood == "BUSY":
             color = QColor(255, 165, 0) # Orange
             # Rapid spinning logic would go here (simplified as color change for now)

        elif self.mood == "ERROR":
            color = QColor(255, 50, 50) # Red
            # Glitch jitter
            import random
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)

        elif self.mood == "SUCCESS":
            color = QColor(50, 255, 50) # Green

        # Draw Glow (Outer)
        gradient = QRadialGradient(x, y, 100 * size_mult)
        gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 150))
        gradient.setColorAt(0.8, QColor(color.red(), color.green(), color.blue(), 20))
        gradient.setColorAt(1, Qt.GlobalColor.transparent)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x - 100*size_mult), int(y - 100*size_mult), int(200*size_mult), int(200*size_mult))

        # Core (Inner)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(color)
        pen.setWidth(4)
        painter.setPen(pen)
        
        # Tech ring
        painter.drawEllipse(int(x - 40), int(y - 20), 80, 40)
        
        # Pupil
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x - 5), int(y - 5), 10, 10)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TessFace()
    sys.exit(app.exec())
