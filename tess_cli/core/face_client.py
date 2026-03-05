import socket
import json
import threading

class FaceClient:
    """Lightweight UDP Client for TESS Face."""
    
    def __init__(self, host='127.0.0.1', port=8005):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def set_mood(self, mood: str):
        """
        Sends a fire-and-forget UDP packet to update the face.
        Moods: IDLE, THINKING, SPEAKING, SUCCESS, ERROR, BUSY
        """
        try:
            msg = json.dumps({"mood": mood.upper()}).encode('utf-8')
            self.sock.sendto(msg, (self.host, self.port))
        except Exception:
            # Sockets might fail if Face isn't running, but we don't want to crash TESS
            pass

    def close(self):
        self.sock.close()
