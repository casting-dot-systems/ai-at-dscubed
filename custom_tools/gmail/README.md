# Gmail Client

This program provides functionality to send and read emails using the Gmail API.

## Setup Instructions

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Cloud Project and enable Gmail API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Create OAuth 2.0 credentials
   - Download the credentials and save them as `credentials.json` in the `secret` folder


3. Create a `.env.development` file with the following variables:
   ```
   GMAIL_USER=your.email@gmail.com
   ```

## Usage

```python
from gmail_client import GmailClient

# Initialize the client
client = GmailClient()

# Send an email
client.send_email(
    to=["recipient1@example.com","recipient2@example.com"],
    subject="Test Email",
    body="This is a test email"
)

# Read recent emails
emails = client.read_emails(max_results=5)
for email in emails:
    print(f"From: {email['sender']}")
    print(f"Subject: {email['subject']}")
    print(f"Body: {email['body']}")
    print("---")

# Reply to email
client.send_email(
    to=["recipient1@example.com","recipient2@example.com"],
    subject="Re: Test Email",
    body="This is a test email",
    references="<MessageID1> <MessageID2> ..."
    in-reply-to="<MessageID1>"
)
```

## Authentication

The program uses OAuth 2.0 for authentication. On first run, it will open a browser window for you to authorize the application. The credentials will be saved in `token.pickle` for future use.

## Features

- Send emails (plain text or HTML)
- Read recent emails from inbox
- Reply emails
- Automatic OAuth2 authentication
- Credential persistence
