"""
Google Client - Gmail and Calendar integration.
Uses Google API with OAuth.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path


class GoogleClient:
    """
    Google API client for Gmail and Calendar.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.creds = None
        self.service_gmail = None
        self.service_calendar = None
        
        if credentials_path is None:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            credentials_path = config.config.google.credentials_file
        
        self.credentials_path = credentials_path
        self.token_path = str(Path(credentials_path).parent / "token.pickle") if credentials_path else "token.pickle"
    
    def _authenticate(self, service_name: str):
        """Authenticate with Google API."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            # Load existing token
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Refresh or create
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path or not os.path.exists(self.credentials_path):
                        return None
                    
                    # Define scopes based on service
                    if service_name == "gmail":
                        scopes = ['https://www.googleapis.com/auth/gmail.modify']
                    else:
                        scopes = ['https://www.googleapis.com/auth/calendar']
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, scopes)
                    self.creds = flow.run_local_server(port=0)
                
                # Save token
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Build service
            if service_name == "gmail":
                self.service_gmail = build('gmail', 'v1', credentials=self.creds)
                return self.service_gmail
            else:
                self.service_calendar = build('calendar', 'v3', credentials=self.creds)
                return self.service_calendar
                
        except ImportError:
            print("Google API libraries not installed.")
            print("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return None
        except Exception as e:
            print(f"Auth error: {e}")
            return None
    
    def list_emails(self, max_results: int = 5) -> str:
        """List recent emails."""
        service = self._authenticate("gmail")
        if not service:
            return "Gmail not authenticated"
        
        try:
            results = service.users().messages().list(
                userId='me', 
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return "No emails found"
            
            output = ["Recent Emails:", "-" * 40]
            
            for msg in messages:
                msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                output.append(f"From: {sender}")
                output.append(f"Subject: {subject}")
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Email error: {e}"
    
    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email."""
        service = self._authenticate("gmail")
        if not service:
            return "Gmail not authenticated"
        
        try:
            from email.mime.text import MIMEText
            import base64
            
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return f"Email sent to {to}"
            
        except Exception as e:
            return f"Send error: {e}"
    
    def list_events(self, max_results: int = 5) -> str:
        """List upcoming calendar events."""
        service = self._authenticate("calendar")
        if not service:
            return "Calendar not authenticated"
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return "No upcoming events"
            
            output = ["Upcoming Events:", "-" * 40]
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No Title')
                output.append(f"{start}: {summary}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Calendar error: {e}"
    
    def create_event(self, summary: str, start_time: str, duration_minutes: int = 60) -> str:
        """Create a calendar event."""
        service = self._authenticate("calendar")
        if not service:
            return "Calendar not authenticated"
        
        try:
            # Parse start time
            # Simple parsing - assumes "tomorrow at 3pm" or ISO format
            if "tomorrow" in start_time.lower():
                start = datetime.now() + timedelta(days=1)
                start = start.replace(hour=15, minute=0)  # Default 3pm
            else:
                start = datetime.now() + timedelta(hours=1)
            
            end = start + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            
            return f"Event created: {event.get('htmlLink')}"
            
        except Exception as e:
            return f"Create error: {e}"
