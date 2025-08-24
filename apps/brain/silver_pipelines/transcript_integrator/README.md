# Transcript Integrator Engine

This engine processes meeting transcripts from Google Drive and automatically populates database tables with meeting information, participants, and project associations.

## Enhanced Summariser

The enhanced summariser (`enhanced_summariser.py`) extends the integrator functionality to:
- Download transcripts from Google Drive
- Generate comprehensive summaries using GPT-4.1
- Update existing meeting records in `meeting.sql` with summaries
- Provide context-aware summaries using project and committee information

## Features

- **Google Drive Integration**: Downloads transcripts directly from Google Drive folders
- **Transcript Processing**: Analyzes meeting transcripts using GPT-4.1 to extract structured information
- **Member Identification**: Matches participants to existing committee members
- **Smart Project Linking**: Uses both GPT analysis and keyword matching from project descriptions
- **Database Integration**: Generates SQL statements with TRUNCATE to replace existing data
- **Google Drive Links**: Stores actual Google Drive file links instead of local paths
- **Async Processing**: Handles multiple transcripts efficiently
- **User Confirmation**: Shows preview of generated SQL before applying changes

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Drive API Setup

Run the setup script to configure Google Drive API credentials:

```bash
python setup_google_drive.py
```

This will guide you through:
1. Creating a Google Cloud Project
2. Enabling the Google Drive API
3. Creating OAuth 2.0 credentials
4. Downloading the credentials file

### 3. Manual Setup (Alternative)

If you prefer to set up manually:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the JSON file and save it as `credentials.json` in this directory

## Usage

### Running the Transcript Integrator

```bash
cd programs/processing_transcripts/transcript_integrator
python transcript_integrator.py
```

### Running the Enhanced Summariser

```bash
cd programs/processing_transcripts/transcript_integrator
python run_summariser.py
# or
python enhanced_summariser.py
```

### Input

- **Google Drive Folder URL**: URL to a Google Drive folder containing transcript files
- **Transcript Files**: Text files (.txt) in the specified Google Drive folder

### Output

#### Transcript Integrator
The integrator generates SQL statements for:
- `meeting.sql`: Meeting metadata (type, date, transcript link)
- `meeting_members.sql`: Meeting participants
- `meeting_projects.sql`: Projects discussed in meetings

#### Enhanced Summariser
The summariser:
- Generates comprehensive meeting summaries using GPT-4.1
- Updates existing meeting records in `meeting.sql` with summaries
- Provides context-aware summaries using project and committee information

## How It Works

1. **Authentication**: Authenticates with Google Drive API using OAuth 2.0
2. **File Download**: Downloads all text files from the specified Google Drive folder
3. **Data Loading**: Loads existing committee members, projects, and project members from SQL files
4. **Transcript Analysis**: Uses GPT-4.1 to extract meeting information from transcripts
5. **Smart Project Linking**: 
   - Uses GPT-identified projects as primary matches
   - Performs keyword matching on project descriptions for additional links
   - Extracts relevant terms like "database", "marathon", "website" from project summaries
6. **SQL Generation**: Creates TRUNCATE + INSERT statements to replace existing data
7. **Google Drive Links**: Stores actual Google Drive file URLs for easy access
8. **User Review**: Shows preview and asks for confirmation before updating files

## Database Schema

### Input Tables (Read)
- `committee.sql`: Committee member information
- `project.sql`: Project definitions
- `project_members.sql`: Project-team associations

### Output Tables (Generated)
- `meeting.sql`: Meeting records
- `meeting_members.sql`: Meeting participants
- `meeting_projects.sql`: Meeting-project associations

## Configuration

### Paths
- **DML Directory**: `brain/processing_transcripts_info/DML/`
- **Credentials**: `credentials.json` (Google Drive API credentials)
- **Token Cache**: `token.pickle` (OAuth token cache)

### Model
- **LLM Provider**: OpenAI GPT-4.1 Mini
- **Prompt Engineering**: Structured extraction of meeting information

### Google Drive API
- **Scopes**: Read-only access to Google Drive
- **Authentication**: OAuth 2.0 with token caching

## Testing

Run the test script to verify the engine works:

```bash
python test_integrator.py
```

## Example Usage

```bash
# Setup Google Drive API (first time only)
python setup_google_drive.py

# Run the integrator
python transcript_integrator.py

# Enter Google Drive folder URL when prompted:
# https://drive.google.com/drive/u/2/folders/1_A946JC2kBc6N6tmI8QPQz6Bj5HlfUsq

# Run the enhanced summariser (after integrator has populated meeting.sql)
python run_summariser.py

# Enter the same Google Drive folder URL to generate summaries
```

## Troubleshooting

### Common Issues

1. **"credentials.json not found"**
   - Run `python setup_google_drive.py` to set up credentials

2. **"Google Drive API not available"**
   - Install dependencies: `pip install -r requirements.txt`

3. **"Invalid Google Drive folder URL"**
   - Make sure the URL points to a Google Drive folder
   - URL should contain `/folders/` or `id=` parameter

4. **"No text files found"**
   - Ensure the folder contains .txt files
   - Check folder permissions

## Dependencies

- `google-auth-oauthlib`: Google OAuth authentication
- `google-auth-httplib2`: Google HTTP client
- `google-api-python-client`: Google Drive API client
- `aiofiles`: Async file operations
- `llmgine`: Core framework
- `openai`: GPT-4.1 API access
- `asyncio`: Async processing support 