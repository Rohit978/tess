import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from .logger import setup_logger

logger = setup_logger("GoogleClient")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar'
]

class GoogleClient:
    """
    Client for interacting with Google APIs (Gmail, Calendar).
    Uses OAuth 2.0 flow for authentication.
    """
    def __init__(self, credentials_path="credentials.json", token_path=None):
        self.credentials_path = credentials_path
        self.token_path = token_path or os.path.join("data", "token.json")
        self.creds = None
        self.gmail_service = None
        self.calendar_service = None
        
        # Ensure data dir exists
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)

    def authenticate(self):
        """Authenticates the user and builds service objects."""
        try:
            # 1. Load existing token
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            # 2. Refresh or Login if invalid
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing Google Token...")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Credentials file not found at: {self.credentials_path}")
                        return False
                        
                    logger.info("Initiating Google Login Flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_path, "w") as token:
                    token.write(self.creds.to_json())
            
            # 3. Build Services
            self.gmail_service = build('gmail', 'v1', credentials=self.creds)
            self.calendar_service = build('calendar', 'v3', credentials=self.creds)
            logger.info("GoogleClient Authenticated Successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Google Auth Failed: {e}")
            return False

    # ==========================
    # GMAIL OPERATIONS
    # ==========================
    
    def list_emails(self, max_results=5):
        if not self.gmail_service and not self.authenticate():
            return "Error: Authentication failed."
            
        try:
            results = self.gmail_service.users().messages().list(
                userId='me', labelIds=['INBOX'], q="is:unread", maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                return "No unread messages found."
            
            output = []
            for i, msg in enumerate(messages):
                txt = self.gmail_service.users().messages().get(
                    userId='me', id=msg['id'], format='minimal'
                ).execute()
                snippet = txt.get('snippet', '')
                output.append(f"{i+1}. {snippet}")
                
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Gmail List Failed: {e}")
            return f"Error listing emails: {e}"

    def send_email(self, to_email, subject, body):
        if not self.gmail_service and not self.authenticate():
            return "Error: Authentication failed."

        try:
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.gmail_service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()
            return f"Email sent successfully to {to_email}"
        except Exception as e:
            logger.error(f"Gmail Send Failed: {e}")
            return f"Error sending email: {e}"

    # ==========================
    # CALENDAR OPERATIONS
    # ==========================
    
    def list_events(self, max_results=5):
        if not self.calendar_service and not self.authenticate():
            return "Error: Authentication failed."
            
        try:
            import datetime
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                return "No upcoming events found."
            
            output = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event['summary']
                output.append(f"- {start}: {summary}")
                
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Calendar List Failed: {e}")
            return f"Error listing events: {e}"

    def create_event(self, summary, start_time_str):
        # NOTE: Parsing natural language time is complex. 
        # For v1, we assume start_time_str is reasonably standard or we use a parser.
        # This is a stub for stricter implementation.
        if not self.calendar_service and not self.authenticate():
            return "Error: Authentication failed."
            
        return "Creating events via API requires strict datetime formats. Feature pending update."
