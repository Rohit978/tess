
import hashlib
import base64
import os
import secrets
import threading
import webbrowser
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# CONFIGURATION (USER MUST FILL THESE)
CLIENT_ID = "YOUR_CANVA_CLIENT_ID"
CLIENT_SECRET = "YOUR_CANVA_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8080/callback"
AUTH_ENDPOINT = "https://www.canva.com/api/oauth/authorize"
TOKEN_ENDPOINT = "https://api.canva.com/rest/v1/oauth/token"

# GLOBAL STATE
auth_code = None
server = None

def generate_pkce():
    """Generates code_verifier and code_challenge for PKCE."""
    code_verifier = secrets.token_urlsafe(96)[:128]
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode('ascii').rstrip('=')
    return code_verifier, code_challenge

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/callback":
            params = parse_qs(parsed_path.query)
            if 'code' in params:
                auth_code = params['code'][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this window.")
                threading.Thread(target=server.shutdown).start()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed.")

def start_server():
    global server
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    server.serve_forever()

def main():
    if CLIENT_ID == "YOUR_CANVA_CLIENT_ID":
        print("❌ Please edit this script and set your CANVA_CLIENT_ID and SECRET.")
        return

    print("🚀 Starting Canva OAuth Flow...")
    verifier, challenge = generate_pkce()

    # 1. Start Local Server
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    # 2. Open Auth URL
    auth_url = (
        f"{AUTH_ENDPOINT}?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=design:content:read design:content:write&"
        f"code_challenge={challenge}&"
        f"code_challenge_method=S256"
    )
    
    print(f"🌐 Opening Browser: {auth_url}")
    webbrowser.open(auth_url)

    # 3. Wait for Code
    server_thread.join()

    if not auth_code:
        print("❌ Failed to get auth code.")
        return

    print(f"✅ Auth Code Received: {auth_code[:10]}...")

    # 4. Exchange for Token
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI
    }

    print("🔄 Exchanging code for token...")
    try:
        response = requests.post(TOKEN_ENDPOINT, data=payload)
        response.raise_for_status()
        tokens = response.json()
        
        print("\n🎉 SUCCESS! Here are your credentials:\n")
        print(f"ACCESS_TOKEN: {tokens.get('access_token')}")
        print(f"REFRESH_TOKEN: {tokens.get('refresh_token')}")
        print(f"EXPIRES_IN: {tokens.get('expires_in')}")
        
    except Exception as e:
        print(f"❌ Token Exchange Failed: {e}")
        print(response.text)

if __name__ == "__main__":
    main()
