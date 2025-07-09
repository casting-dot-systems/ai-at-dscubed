import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional


# there are no types for googleapis bruh
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://mail.google.com/",
]

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_PATH = os.path.join(SCRIPT_DIR, "secrets/client_secret.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "secrets/token.json")


def __authenticate() -> Any:
    
    """Authenticate with Gmail API using OAuth2."""
    # Check if token.json exists
    if os.path.exists(TOKEN_PATH):
        creds : Credentials = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)  # type: ignore

        # If credentials are not valid or don't exist, get new ones
        if not creds or not creds.valid:
            
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_PATH, SCOPES, redirect_uri="http://localhost:8080/"
                )
                creds = flow.run_local_server(port=8080)

            # Save credentials for future use
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

    service: Any = build("gmail", "v1", credentials=creds)  # type: ignore
    return service


def send_email(to: str, subject: str, body: str, is_html: bool = False) -> bool:
    """
    Send an email using Gmail API.

    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body content
        is_html: Whether the body is HTML content

    Returns:
        bool: True if email was sent successfully, False otherwise
    """

    service = __authenticate()
    try:
        # Create the email message
        message = __create_message(to, subject, body, is_html)

        # Send message
        service.users().messages().send(userId="me", body=message).execute()

        return True
    except Exception as e:
        print(f"Error sending email: {e!s}")
        return False



email_dict_type = dict[Any, Any]


def read_emails(max_results: int = 10) -> list[email_dict_type]:
    """
    Read recent emails from the inbox.

    Args:
        max_results: Maximum number of emails to retrieve

    Returns:
        List of dictionaries containing email details
    """
    service = __authenticate()
    try:
        # Get a list of emails from recent inbox
        results = (
            service.users().messages().list(userId="me", maxResults=max_results).execute()
        )
        messages = results.get("messages", [])
        emails : list[email_dict_type] = []

        # Get the email details
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()

            processed_email : email_dict_type = __process_email(msg)
            emails.append(processed_email)

        return emails
    
    except Exception as e:
        print(f"Error reading emails: {e!s}")
        return []


def __process_email(email: email_dict_type) -> email_dict_type:
    """
    Process an email and extract relevant information.

    Args:
        email: raw dictionary containing email details sent from gmail api

    Returns:
        Dictionary containing processed email information
    """

    processed_email : email_dict_type = {}

    # Get the id
    processed_email["id"] = email["id"]

    # Get the main headers
    processed_email["headers"] = []
    for header in email["payload"]["headers"]:
        if not header["name"].startswith("X-"):

            processed_email["headers"].append(header)

    # Get message body
    if "parts" in email["payload"]:
        body = email["payload"]["parts"][0]["body"].get("data", "")
    else:
        body = email["payload"]["body"].get("data", "")
    # Decode the body
    if body:
        body = base64.urlsafe_b64decode(body.encode("ASCII")).decode("utf-8")

    processed_email["body"] = body
    return processed_email


def reply_to_email(email_id: str, body: str, is_html: bool = False) -> bool:
    """
    Reply to an email using Gmail API.

    Args:
        email_id: ID of the email to reply to
        body: Body of the email
        is_html: Whether the body is HTML content

    Returns:
        bool: True if email was sent successfully, False otherwise
    """

    service = __authenticate()
    try:
        # Get the email to reply to
        email = service.users().messages().get(userId="me", id=email_id).execute()
        headers = email["payload"]["headers"]

        # Get the original message ID
        original_message_id : Optional[str] = next(
            (
                header["value"]
                for header in headers
                if header["name"].lower() == "message-id"
            ),
            None,
        )

        # Get the references chain
        references : Optional[str] = next(
            (
                header["value"]
                for header in headers
                if header["name"].lower() == "references"
            ),
            "",
        )
        if references:
            references = f"{references} {original_message_id}"
        else:
            references = original_message_id

        # Get the reply-to address (if exists) or from address
        reply_to = next(
            (
                header["value"]
                for header in headers
                if header["name"].lower() == "reply-to"
            ),
            None,
        )
        to = (
            reply_to
            if reply_to
            else next(
                header["value"] for header in headers if header["name"].lower() == "from"
            )
        )

        # Get the subject and add Re: prefix if not already present
        subject = next(
            header["value"] for header in headers if header["name"].lower() == "subject"
        )
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"


        assert references is not None

        # Create the email message with threading information
        message: dict[str, str] = __create_message(
            to=to,
            subject=subject,
            body=body,
            is_html=is_html,
            original_message_id=original_message_id,
            references=references,
        )

        # Send the email
        service.users().messages().send(userId="me", body=message).execute()

        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def __create_message(
    to: str,
    subject: str,
    body: str,
    is_html: bool = False,
    original_message_id: Optional[str] = None,
    reply_to: Optional[str] = None,
    references: str = "",
) -> dict[str, str]:
    """
    Create an email message for sending or replying.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        is_html: Whether the body is HTML content
        original_message_id: ID of the original message being replied to (for threading)
        reply_to: Reply-to email address
        references: References chain for threading

    Returns:
        dict: A dictionary containing the raw email message
    """
    message = MIMEMultipart()
    message["To"] = to
    message["Subject"] = subject

    # Add threading headers if replying to an email
    if original_message_id:
        message["References"] = references
        message["In-Reply-To"] = original_message_id

    if reply_to:
        message["Reply-To"] = reply_to

    # Attach body
    if is_html:
        msg = MIMEText(body, "html")
    else:
        msg = MIMEText(body)
    message.attach(msg)

    # Encode message
    raw_message: str = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}  # TODO why is this a dict?
