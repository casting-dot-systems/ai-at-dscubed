# gmail_tools.py
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

from __future__ import annotations
import os
import base64
import re
from email import message_from_bytes
from email.message import EmailMessage
from email.header import decode_header

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---- Config ----
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
CLIENT_SECRET_FILE = "client_secret.json"  # change to your exact filename if different

# ---- Auth / Service ----
def get_service():
    """Authorize the user and return a Gmail API service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ---- Helpers ----
def _decode_header_value(val: str | None) -> str:
    if not val:
        return ""
    parts = decode_header(val)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def extract_plain_text(msg) -> str:
    """
    Best-effort plain-text extractor:
    - Prefer text/plain (skip attachments)
    - Fallback to text/html with simple tag stripping
    """
    if msg.is_multipart():
        # Prefer text/plain
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", "replace"
                )
        # Fallback to HTML
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                html = part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", "replace"
                )
                html = re.sub(r"(?i)<br\s*/?>", "\n", html)
                return re.sub(r"<[^>]+>", "", html)
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload is None:
            return msg.get_payload() or ""
        return payload.decode(msg.get_content_charset() or "utf-8", "replace")


# ---- Features ----
def list_labels(service):
    """Print all labels."""
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    for label in labels:
        print(f"{label['name']} ({label['id']})")


def send_email(service, to_addr: str, subject: str, body_text: str):
    """Send a simple plain-text email."""
    msg = EmailMessage()
    msg["To"] = to_addr
    msg["From"] = "me"
    msg["Subject"] = subject
    msg.set_content(body_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Message sent, id: {sent['id']}")


def find_recent_emails(service, query: str = "newer_than:7d", max_results: int = 3):
    """
    Find recent emails with a Gmail search query (e.g., 'label:inbox newer_than:3d is:unread').
    Prints From / Date / Subject and the email body (plain-text with HTML fallback).
    """
    resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = resp.get("messages", [])
    if not messages:
        print("No matching messages.")
        return

    for m in messages:
        raw_resp = service.users().messages().get(
            userId="me", id=m["id"], format="raw"  # must be lowercase 'raw'
        ).execute()
        mime_bytes = base64.urlsafe_b64decode(raw_resp["raw"])
        mime_msg = message_from_bytes(mime_bytes)

        from_ = _decode_header_value(mime_msg.get("From"))
        subj = _decode_header_value(mime_msg.get("Subject"))
        date = _decode_header_value(mime_msg.get("Date"))
        body = extract_plain_text(mime_msg).strip()

        print(f"From: {from_}")
        print(f"Date: {date}")
        print(f"Subject: {subj}")
        print("Body:")
        print(body if body else "(no body)")
        print("-" * 60)


# ---- Example usage ----
if __name__ == "__main__":
    svc = get_service()

    print("Your labels:")
    list_labels(svc)

    # Example send (uncomment and edit to use)
    # send_email(svc, "someone@example.com", "Hello from Gmail API", "It works!")

    print("\nRecent emails (last 7 days):")
    find_recent_emails(svc, query="label:inbox newer_than:7d", max_results=3)
