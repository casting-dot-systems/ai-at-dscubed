import os
import asyncio
import uuid
import aiofiles
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path
import urllib.parse

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.ui.cli.cli import EngineCLI
from llmgine.ui.cli.components import EngineResultComponent

# Google Drive API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
    import pickle
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Warning: Google Drive API not available. Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")

# Paths
DML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../brain/processing_transcripts_info/DML'))

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

@dataclass
class SummariseTranscriptsCommand(Command):
    google_drive_folder_url: str = ""

@dataclass
class SummariseStatusEvent(Event):
    status: str = ""
    current_file: str = ""

@dataclass
class SummariseResultEvent(Event):
    summaries_generated: int = 0
    meeting_updates: int = 0

class EnhancedSummariserEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(uuid.uuid4())
        
        # Load existing data
        self.committee_members = self._load_committee_members()
        self.projects = self._load_projects()
        self.project_members = self._load_project_members()
        self.meetings = self._load_existing_meetings()
        
        # Google Drive service
        self.drive_service = None

    def _load_committee_members(self) -> Dict[str, Dict]:
        """Load committee members from committee.sql"""
        members = {}
        committee_file = os.path.join(DML_DIR, 'committee.sql')
        
        if os.path.exists(committee_file):
            with open(committee_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse INSERT statements - updated for silver schema and ingestion_timestamp
                # Pattern: (1, 'John', 'Doe', 'john.doe@example.com', '2021-01-01', 'AI Engineer', 'Active', CURRENT_TIMESTAMP)
                matches = re.findall(r"\((\d+), '([^']+)', '([^']+)', '[^']+', '[^']+', '[^']+', '[^']+', [^)]+\)", content)
                for member_id, first_name, last_name in matches:
                    full_name = f"{first_name} {last_name}"
                    members[full_name.lower()] = {
                        'id': int(member_id),
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': full_name
                    }
        return members

    def _load_projects(self) -> Dict[str, Dict]:
        """Load projects from project.sql"""
        projects = {}
        project_file = os.path.join(DML_DIR, 'project.sql')
        
        if os.path.exists(project_file):
            with open(project_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Parse INSERT statements - handle new structure with project_name and project_description
                # Look for pattern: (1, 'Even''s Marathon', 'Organizing a charity marathon event led by Even.', CURRENT_TIMESTAMP)
                matches = re.findall(r"\((\d+), '([^']*(?:''[^']*)*)', '([^']*(?:''[^']*)*)', [^)]+\)", content)
                
                for project_id, project_name, project_description in matches:
                    # Unescape the quotes
                    project_name = project_name.replace("''", "'")
                    project_description = project_description.replace("''", "'")
                    
                    projects[project_name.lower()] = {
                        'id': int(project_id),
                        'name': project_name,
                        'summary': project_description  # Keep 'summary' key for backward compatibility
                    }
        return projects

    def _load_project_members(self) -> Dict[int, List[int]]:
        """Load project members from project_members.sql"""
        project_members = {}
        project_members_file = os.path.join(DML_DIR, 'project_members.sql')
        
        if os.path.exists(project_members_file):
            with open(project_members_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse INSERT statements - updated for silver schema and ingestion_timestamp
                # Pattern: (1, 1, CURRENT_TIMESTAMP)
                matches = re.findall(r"\((\d+), (\d+), [^)]+\)", content)
                for project_id, member_id in matches:
                    project_id = int(project_id)
                    member_id = int(member_id)
                    if project_id not in project_members:
                        project_members[project_id] = []
                    project_members[project_id].append(member_id)
        return project_members

    def _load_existing_meetings(self) -> Dict[str, Dict]:
        """Load existing meetings from meeting.sql"""
        meetings = {}
        meeting_file = os.path.join(DML_DIR, 'meeting.sql')
        
        if os.path.exists(meeting_file):
            with open(meeting_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse INSERT statements - updated for silver schema and ingestion_timestamp
                # Pattern: (1, 'Project Discussion', 'transcript_link', '2024-06-08', 'summary', CURRENT_TIMESTAMP)
                # Handle the case where meeting_summary might be empty
                matches = re.findall(r"\((\d+), '([^']+)', '([^']+)', '([^']+)', '([^']*)', [^)]+\)", content)
                for meeting_id, meeting_type, transcript_link, date, summary in matches:
                    meetings[transcript_link] = {
                        'meeting_id': int(meeting_id),
                        'type': meeting_type,
                        'transcript_link': transcript_link,
                        'date': date,
                        'summary': summary
                    }
        return meetings

    async def handle_command(self, command: Command) -> CommandResult:
        try:
            if isinstance(command, SummariseTranscriptsCommand):
                google_drive_url = command.google_drive_folder_url
            else:
                google_drive_url = getattr(command, 'google_drive_folder_url', None)
                if not google_drive_url:
                    raise ValueError("No google_drive_folder_url provided in command.")
            
            result = await self.summarise_transcripts(google_drive_url)
            return CommandResult(success=True, result=result, session_id=self.session_id)
        except Exception as e:
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def summarise_transcripts(self, google_drive_url: str) -> Dict:
        """Main summarisation process"""
        await self.bus.publish(SummariseStatusEvent(
            status="Starting transcript summarisation", 
            session_id=self.session_id
        ))
        
        # Initialize Google Drive service
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ValueError("Google Drive API not available. Please install required packages.")
        
        await self.bus.publish(SummariseStatusEvent(
            status="Authenticating with Google Drive", 
            session_id=self.session_id
        ))
        
        self.drive_service = await self._authenticate_google_drive()
        
        # Extract folder ID from URL
        folder_id = self._extract_folder_id_from_url(google_drive_url)
        if not folder_id:
            raise ValueError("Invalid Google Drive folder URL")
        
        await self.bus.publish(SummariseStatusEvent(
            status="Downloading transcripts from Google Drive", 
            session_id=self.session_id
        ))
        
        # Download transcript files from Google Drive
        transcript_files = await self._download_transcripts_from_drive(folder_id)
        
        await self.bus.publish(SummariseStatusEvent(
            status=f"Found {len(transcript_files)} transcript files", 
            session_id=self.session_id
        ))
        
        summaries_generated = 0
        meeting_updates = 0
        
        for transcript_file in transcript_files:
            await self.bus.publish(SummariseStatusEvent(
                status="Generating summary", 
                current_file=transcript_file['file_name'],
                session_id=self.session_id
            ))
            
            summary = await self._generate_summary(transcript_file)
            if summary:
                summaries_generated += 1
                # Update meeting.sql if this transcript is already in the database
                if await self._update_meeting_summary(transcript_file['drive_link'], summary):
                    meeting_updates += 1
        
        await self.bus.publish(SummariseResultEvent(
            summaries_generated=summaries_generated,
            meeting_updates=meeting_updates,
            session_id=self.session_id
        ))
        
        return {
            'summaries_generated': summaries_generated,
            'meeting_updates': meeting_updates
        }

    def _extract_folder_id_from_url(self, url: str) -> Optional[str]:
        """Extract folder ID from Google Drive URL"""
        # Handle different Google Drive URL formats
        patterns = [
            r'/folders/([a-zA-Z0-9_-]+)',  # Standard folder URL
            r'id=([a-zA-Z0-9_-]+)',        # URL with id parameter
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    async def _authenticate_google_drive(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
        credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        
        # Load existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials available, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    print("Google Drive API credentials not found.")
                    print("Please download credentials.json from Google Cloud Console and place it in this directory.")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a project and enable Google Drive API")
                    print("3. Create credentials (OAuth 2.0 Client ID)")
                    print("4. Download the JSON file and rename it to credentials.json")
                    raise FileNotFoundError("credentials.json not found")
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the service
        return build('drive', 'v3', credentials=creds)

    async def _download_transcripts_from_drive(self, folder_id: str) -> List[Dict]:
        """Download transcript files from Google Drive folder"""
        transcript_files = []
        
        try:
            # List files in the folder
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='text/plain'",
                fields="files(id, name, mimeType, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                print("No text files found in the specified folder.")
                return []
            
            # Create temporary directory for downloads
            temp_dir = tempfile.mkdtemp()
            
            for file in files:
                file_id = file['id']
                file_name = file['name']
                web_view_link = file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
                
                print(f"Downloading: {file_name}")
                
                # Download file
                request = self.drive_service.files().get_media(fileId=file_id)
                file_path = os.path.join(temp_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        if status:
                            print(f"Downloaded {int(status.progress() * 100)}% of {file_name}")
                
                transcript_files.append({
                    'local_path': file_path,
                    'drive_link': web_view_link,
                    'file_name': file_name
                })
            
            return transcript_files
            
        except Exception as e:
            print(f"Error downloading files from Google Drive: {e}")
            return []

    async def _generate_summary(self, transcript_file: Dict) -> Optional[str]:
        """Generate summary for a single transcript file"""
        try:
            with open(transcript_file['local_path'], 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            
            # Create enhanced prompt with project context
            prompt = f"""
You are an expert meeting summariser. Given the following meeting transcript and project information, write a concise but detailed summary of the meeting.

Available projects and their descriptions:
{self._format_projects()}

Available committee members:
{self._format_committee_members()}

Please analyze the meeting transcript and create a comprehensive summary that:
1. Identifies the main topics discussed
2. Lists key decisions made
3. Mentions any action items or next steps
4. Relates discussions to relevant projects when possible
5. Identifies which committee members participated in key discussions
6. Highlights any important deadlines or milestones mentioned

Meeting Transcript:
{transcript_content}

Write a clear, structured summary that captures the essential information from this meeting:
"""
            
            response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
            summary = response.raw.choices[0].message.content or ""
            
            if summary:
                print(f"Generated summary for {transcript_file['file_name']}")
                return summary.strip()
            else:
                print(f"No summary generated for {transcript_file['file_name']}")
                return None
                
        except Exception as e:
            print(f"Error generating summary for {transcript_file['file_name']}: {e}")
            return None
    async def _update_meeting_summary(self, transcript_link: str, summary: str) -> bool:
        """Update meeting.sql with the generated summary"""
        try:
            # Check if this transcript is already in the meetings table
            if transcript_link in self.meetings:
                meeting = self.meetings[transcript_link]
                
                # Read the current meeting.sql file
                meeting_file = os.path.join(DML_DIR, 'meeting.sql')
                with open(meeting_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Escape single quotes in summary for SQL
                escaped_summary = summary.replace("'", "''")
                
                # Replace the empty summary with the generated summary
                # Pattern: (meeting_id, 'type', 'transcript_link', 'date', '', CURRENT_TIMESTAMP)
                # We need to match the exact pattern including CURRENT_TIMESTAMP
                old_pattern = f"({meeting['meeting_id']}, '{meeting['type']}', '{meeting['transcript_link']}', '{meeting['date']}', '', CURRENT_TIMESTAMP)"
                new_pattern = f"({meeting['meeting_id']}, '{meeting['type']}', '{meeting['transcript_link']}', '{meeting['date']}', '{escaped_summary}', CURRENT_TIMESTAMP)"
                
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    
                    # Write back to file
                    async with aiofiles.open(meeting_file, 'w', encoding='utf-8') as f:
                        await f.write(content)
                    
                    print(f"Updated meeting {meeting['meeting_id']} with summary")
                    return True
                else:
                    print(f"Could not find exact pattern to update for meeting {meeting['meeting_id']}")
                    return False
            else:
                print(f"Transcript link not found in meetings table: {transcript_link}")
                return False
                
        except Exception as e:
            print(f"Error updating meeting summary: {e}")
            return False

    def _format_committee_members(self) -> str:
        """Format committee members for prompt"""
        return "\n".join([f"- {member['full_name']}" for member in self.committee_members.values()])

    def _format_projects(self) -> str:
        """Format projects for prompt"""
        return "\n".join([f"- {project['name']}: {project['summary']}" for project in self.projects.values()])

async def generate_summary_async(transcript_path: str, projects: dict, committee_members: dict) -> str:
    """
    Generate a meeting summary for a transcript file, given project and committee context.
    This is a wrapper for use by transcript_integrator.py.
    """
    # Minimal model stub for compatibility (should be replaced by actual model in main engine)
    from llmgine.llm.models.openai_models import Gpt41Mini
    from llmgine.llm.providers.providers import Providers
    model = Gpt41Mini(Providers.OPENAI)
    # Read transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript_content = f.read()
    # Build context
    project_context = "\n".join([f"- {p['name']}: {p.get('summary', '')}" for p in projects.values()])
    committee_context = "\n".join([f"- {m['name'] if 'name' in m else m.get('full_name', '')}" for m in committee_members.values()])
    prompt = f"""
You are an expert meeting summariser. Given the following meeting transcript and project information, write a concise but detailed summary of the meeting.

Available projects and their descriptions:
{project_context}

Available committee members:
{committee_context}

Please analyze the meeting transcript and create a comprehensive summary that:
1. Identifies the main topics discussed
2. Lists key decisions made
3. Mentions any action items or next steps
4. Relates discussions to relevant projects when possible
5. Identifies which committee members participated in key discussions
6. Highlights any important deadlines or milestones mentioned

Meeting Transcript:
{transcript_content}

Write a clear, structured summary that captures the essential information from this meeting:
"""
    response = await model.generate(messages=[{"role": "user", "content": prompt}])
    summary = response.raw.choices[0].message.content or ""
    return summary.strip() if summary else ""

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    
    model = Gpt41Mini(Providers.OPENAI)
    engine = EnhancedSummariserEngine(model)
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(SummariseTranscriptsCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(SummariseStatusEvent)
    
    # Get Google Drive folder URL
    print("Enhanced Transcript Summariser")
    print("=" * 40)
    print("This engine will download transcripts from Google Drive, generate summaries,")
    print("and update the meeting.sql file with the summaries.")
    print("Make sure you have set up Google Drive API credentials (credentials.json)")
    print()
    
    google_drive_url = input("Enter Google Drive folder URL: ").strip()
    
    if not google_drive_url:
        print("No URL provided. Exiting.")
        return
    
    # Run the engine
    command = SummariseTranscriptsCommand(google_drive_folder_url=google_drive_url)
    result = await engine.handle_command(command)
    
    if result.success:
        print("\n===== SUMMARISATION RESULTS =====\n")
        data = result.result
        print(f"Summaries generated: {data['summaries_generated']}")
        print(f"Meeting records updated: {data['meeting_updates']}")
        
        if data['meeting_updates'] > 0:
            print("\nMeeting summaries have been updated in meeting.sql!")
        else:
            print("\nNo meeting records were updated. Make sure the transcripts")
            print("correspond to existing meetings in the database.")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main()) 