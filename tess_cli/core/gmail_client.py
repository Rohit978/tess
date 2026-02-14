import os.path
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .logger import setup_logger

logger = setup_logger("GmailClient")

# If modifying these scopes, delete the file token_gmail.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailClient:
    """
    Handles Gmail API interactions.
    Requires 'credentials.json' in the project root.
    """
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.is_authenticated = False
        
        # Paths
        self.root_dir = os.getcwd()
        self.creds_path = os.path.join(self.root_dir, 'credentials.json')
        self.token_path = os.path.join(self.root_dir, 'token_gmail.json') # Distinct token for Gmail
        
        self.authenticate()

    def authenticate(self):
        """Authenticates with Google API."""
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.error(f"Invalid Gmail token: {e}")
                
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                     logger.error(f"Gmail Token refresh failed: {e}")
            elif os.path.exists(self.creds_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open(self.token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                     logger.error(f"Gmail OAuth flow failed: {e}")
                     return
            else:
                logger.warning("No 'credentials.json' found. Gmail features disabled.")
                return

        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.is_authenticated = True
            logger.info("Gmail API Authenticated Successfully.")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")

    def get_unread_messages(self, max_results=5):
        """Fetches unread messages."""
        if not self.is_authenticated:
            return "Error: Gmail not authenticated."
            
        try:
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
            messages = results.get('messages', [])

            if not messages:
                return "No unread messages found."

            output = "📧 Unread Emails:\n"
            for msg in messages:
                txt = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = txt['payload']
                headers = payload['headers']
                
                subject = "No Subject"
                sender = "Unknown"
                
                for d in headers:
                    if d['name'] == 'Subject':
                        subject = d['value']
                    if d['name'] == 'From':
                        sender = d['value']
                
                snippet = txt.get('snippet', '')
                output += f"- From: {sender}\n  Subject: {subject}\n  Snippet: {snippet}\n\n"
                
            return output

        except Exception as e:
            return f"Error fetching emails: {e}"

    def send_message(self, to_email, subject, body):
        """Sends an email."""
        if not self.is_authenticated:
            return "Error: Gmail not authenticated."
            
        try:
            message = EmailMessage()
            message.set_content(body)
            message['To'] = to_email
            message['From'] = 'me' # Authenticated user
            message['Subject'] = subject

            # Encode the message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': encoded_message}
            
            send_message = self.service.users().messages().send(userId="me", body=create_message).execute()
            return f"Email sent to {to_email}. Id: {send_message['id']}"
            
        except Exception as e:
             return f"Error sending email: {e}"
