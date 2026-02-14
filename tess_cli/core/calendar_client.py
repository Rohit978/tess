import datetime
import os.path
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .logger import setup_logger

logger = setup_logger("CalendarClient")

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarClient:
    """
    Handles Google Calendar interactions.
    Requires 'credentials.json' in the project root.
    """
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.is_authenticated = False
        
        # Paths
        self.root_dir = os.getcwd()
        self.creds_path = os.path.join(self.root_dir, 'credentials.json')
        self.token_path = os.path.join(self.root_dir, 'token.json')
        
        self.authenticate()

    def authenticate(self):
        """Authenticates with Google API."""
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.error(f"Invalid token: {e}")
                
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                     logger.error(f"Token refresh failed: {e}")
            elif os.path.exists(self.creds_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open(self.token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                     logger.error(f"OAuth flow failed: {e}")
                     return
            else:
                logger.warning("No 'credentials.json' found. Calendar features disabled.")
                return

        try:
            self.service = build('calendar', 'v3', credentials=self.creds)
            self.is_authenticated = True
            logger.info("Calendar API Authenticated Successfully.")
        except Exception as e:
            logger.error(f"Failed to build service: {e}")

    def list_events(self, max_results=10):
        """List upcoming events."""
        if not self.is_authenticated:
            return "Error: Calendar not authenticated. Please provide 'credentials.json'."
            
        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            events_result = self.service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                return "No upcoming events found."
                
            result = "Upcoming Events:\n"
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                result += f"- {start}: {event['summary']}\n"
            return result
            
        except Exception as e:
            return f"Error listing events: {e}"

    def create_event(self, summary, start_time, duration_minutes=60):
        """Create a new event."""
        if not self.is_authenticated:
            return "Error: Calendar not authenticated."
            
        try:
            # Parse start_time (Simple ISO check)
            # In a real app, use python-dateutil for robust parsing
            # For now sending raw or assuming ISO string
            
            # Simple assumption: start_time is ISO string. 
            # If "tomorrow at 5pm", LLM should have converted it.
            
            start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'UTC'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'UTC'},
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {event.get('htmlLink')}"
            
        except Exception as e:
            return f"Error creating event: {e}"

    def delete_event(self, event_id):
        """Delete an event by ID."""
        if not self.is_authenticated:
             return "Error: Calendar not authenticated."
             
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return "Event deleted."
        except Exception as e:
            return f"Error deleting event: {e}"
