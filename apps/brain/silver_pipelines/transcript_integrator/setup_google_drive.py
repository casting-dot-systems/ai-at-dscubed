#!/usr/bin/env python3
"""
Setup script for Google Drive API credentials
"""

import os
import sys
import webbrowser
from pathlib import Path

def main():
    print("Google Drive API Setup")
    print("=" * 40)
    print()
    print("This script will help you set up Google Drive API credentials.")
    print()
    
    # Check if credentials already exist
    credentials_path = Path(__file__).parent / "credentials.json"
    if credentials_path.exists():
        print("✓ credentials.json already exists!")
        print("You can now run the transcript integrator.")
        return
    
    print("To use the Google Drive API, you need to:")
    print("1. Create a Google Cloud Project")
    print("2. Enable the Google Drive API")
    print("3. Create OAuth 2.0 credentials")
    print("4. Download the credentials file")
    print()
    
    # Step 1: Create Google Cloud Project
    print("Step 1: Create a Google Cloud Project")
    print("- Go to https://console.cloud.google.com/")
    print("- Click 'Select a project' → 'New Project'")
    print("- Give it a name (e.g., 'Transcript Integrator')")
    print("- Click 'Create'")
    print()
    
    input("Press Enter when you've created the project...")
    
    # Step 2: Enable Google Drive API
    print("Step 2: Enable Google Drive API")
    print("- In your project, go to 'APIs & Services' → 'Library'")
    print("- Search for 'Google Drive API'")
    print("- Click on it and press 'Enable'")
    print()
    
    input("Press Enter when you've enabled the API...")
    
    # Step 3: Create credentials
    print("Step 3: Create OAuth 2.0 Credentials")
    print("- Go to 'APIs & Services' → 'Credentials'")
    print("- Click 'Create Credentials' → 'OAuth client ID'")
    print("- If prompted, configure the OAuth consent screen:")
    print("  - User Type: Internal")
    print("  - App name: Transcript Integrator")
    print("  - User support email: your email")
    print("  - Developer contact email: your email")
    print("- For OAuth client ID:")
    print("  - Application type: Desktop application")
    print("  - Name: Transcript Integrator")
    print("  - Click 'Create'")
    print()
    
    input("Press Enter when you've created the credentials...")
    
    # Step 4: Download credentials
    print("Step 4: Download Credentials")
    print("- After creating credentials, click 'Download JSON'")
    print("- Save the file as 'credentials.json' in this directory:")
    print(f"  {Path(__file__).parent}")
    print()
    
    # Open the credentials page
    print("Opening Google Cloud Console credentials page...")
    webbrowser.open("https://console.cloud.google.com/apis/credentials")
    
    input("Press Enter when you've downloaded credentials.json to this directory...")
    
    # Verify credentials file
    if credentials_path.exists():
        print("✓ credentials.json found!")
        print("✓ Setup complete!")
        print()
        print("You can now run the transcript integrator:")
        print("python transcript_integrator.py")
    else:
        print("✗ credentials.json not found in this directory.")
        print("Please make sure you downloaded it to:")
        print(f"  {Path(__file__).parent}")
        print()
        print("The file should be named exactly 'credentials.json'")

if __name__ == "__main__":
    main() 