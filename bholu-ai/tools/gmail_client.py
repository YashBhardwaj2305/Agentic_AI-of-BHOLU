"""
Gmail Client — reads real Gmail inbox via Gmail API with OAuth2.
Read-only access only (gmail.readonly scope).
"""

import base64
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EmailMessage

# Read-only scope — never requests write access
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Handles Gmail API authentication and inbox fetching."""

    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json") -> None:
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._service = None

    def authenticate(self) -> None:
        """Authenticate with Gmail API. Uses cached token if valid, else launches OAuth2 flow."""
        creds = None

        # Load existing token if available
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception:
                creds = None

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    print(
                        "[ERROR] credentials.json not found.\n"
                        "Please follow the setup instructions in README.md to:\n"
                        "  1. Create a Google Cloud project\n"
                        "  2. Enable the Gmail API\n"
                        "  3. Download credentials.json to this directory"
                    )
                    sys.exit(1)

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"[ERROR] Failed to load credentials.json: {e}\n"
                          "Please check the file is a valid OAuth2 client secrets file.")
                    sys.exit(1)

            # Save token for future runs
            try:
                self.token_path.write_text(creds.to_json())
            except Exception:
                pass  # Non-fatal: token caching failure

        self._service = build("gmail", "v1", credentials=creds)

    def fetch_inbox(self, count: int = 5) -> list:
        """Fetch the N most recent inbox messages. Returns list of EmailMessage."""
        if self._service is None:
            raise RuntimeError("Call authenticate() before fetch_inbox()")

        try:
            results = (
                self._service.users()
                .messages()
                .list(userId="me", labelIds=["INBOX"], maxResults=count)
                .execute()
            )
        except HttpError as e:
            print(f"[ERROR] Gmail API request failed: {e}")
            sys.exit(1)

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            try:
                msg = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="full")
                    .execute()
                )
                email = self._parse_message(msg)
                emails.append(email)
            except HttpError as e:
                print(f"[WARNING] Failed to fetch message {msg_ref['id']}: {e}")
                continue

        return emails

    def _parse_message(self, msg: dict) -> EmailMessage:
        """Extract sender, subject, and plain-text body from a Gmail message object."""
        headers = msg.get("payload", {}).get("headers", [])
        sender = ""
        subject = ""

        for header in headers:
            name = header.get("name", "").lower()
            if name == "from":
                sender = header.get("value", "")
            elif name == "subject":
                subject = header.get("value", "")

        body = self._extract_plain_text(msg.get("payload", {}))
        return EmailMessage(sender=sender, subject=subject, body=body)

    def _extract_plain_text(self, payload: dict) -> str:
        """Recursively extract plain-text body from message payload. Returns empty string if not found."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                except Exception:
                    return ""
            return ""

        # Recurse into multipart
        for part in payload.get("parts", []):
            result = self._extract_plain_text(part)
            if result:
                return result

        return ""
