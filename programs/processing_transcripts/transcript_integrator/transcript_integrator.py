import os
import asyncio
import uuid
import aiofiles
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Set, Tuple
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
class IntegrateTranscriptsCommand(Command):
    google_drive_folder_url: str = ""

@dataclass
class IntegrationStatusEvent(Event):
    status: str = ""
    current_file: str = ""

@dataclass
class IntegrationResultEvent(Event):
    meetings_processed: int = 0
    members_identified: int = 0
    projects_linked: int = 0

class TranscriptIntegratorEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(uuid.uuid4())
        
        # Load existing data
        self.committee_members = self._load_committee_members()
        self.projects = self._load_projects()
        self.project_members = self._load_project_members()
        
        # Results storage
        self.meetings_data = []
        self.meeting_members_data = []
        self.meeting_projects_data = []
        
        # Google Drive service
        self.drive_service = None

    def _load_committee_members(self) -> Dict[str, Dict]:
        """Load committee members from committee.sql"""
        members = {}
        committee_file = os.path.join(DML_DIR, 'committee.sql')
        
        if os.path.exists(committee_file):
            with open(committee_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse INSERT statements
                matches = re.findall(r"\((\d+), '([^']+)', '([^']+)', '[^']+', '[^']+', '[^']+', '[^']+'\)", content)
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
                
                # Parse INSERT statements - handle escaped quotes
                # Look for pattern: (1, 'Even''s Marathon: ...')
                matches = re.findall(r"\((\d+), '([^']*(?:''[^']*)*)'\)", content)
                
                for project_id, summary in matches:
                    # Extract project name from summary (before the colon)
                    project_name = summary.split(':')[0].strip()
                    # Unescape the quotes
                    project_name = project_name.replace("''", "'")
                    summary = summary.replace("''", "'")
                    
                    projects[project_name.lower()] = {
                        'id': int(project_id),
                        'name': project_name,
                        'summary': summary
                    }
        return projects

    def _load_project_members(self) -> Dict[int, List[int]]:
        """Load project members from project_members.sql"""
        project_members = {}
        project_members_file = os.path.join(DML_DIR, 'project_members.sql')
        
        if os.path.exists(project_members_file):
            with open(project_members_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse INSERT statements
                matches = re.findall(r"\((\d+), (\d+)\)", content)
                for project_id, member_id in matches:
                    project_id = int(project_id)
                    member_id = int(member_id)
                    if project_id not in project_members:
                        project_members[project_id] = []
                    project_members[project_id].append(member_id)
        return project_members

    async def handle_command(self, command: Command) -> CommandResult:
        try:
            if isinstance(command, IntegrateTranscriptsCommand):
                google_drive_url = command.google_drive_folder_url
            else:
                google_drive_url = getattr(command, 'google_drive_folder_url', None)
                if not google_drive_url:
                    raise ValueError("No google_drive_folder_url provided in command.")
            
            result = await self.integrate_transcripts(google_drive_url)
            return CommandResult(success=True, result=result, session_id=self.session_id)
        except Exception as e:
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def integrate_transcripts(self, google_drive_url: str) -> Dict:
        """Main integration process"""
        await self.bus.publish(IntegrationStatusEvent(
            status="Starting transcript integration", 
            session_id=self.session_id
        ))
        
        # Initialize Google Drive service
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ValueError("Google Drive API not available. Please install required packages.")
        
        await self.bus.publish(IntegrationStatusEvent(
            status="Authenticating with Google Drive", 
            session_id=self.session_id
        ))
        
        self.drive_service = await self._authenticate_google_drive()
        
        # Extract folder ID from URL
        folder_id = self._extract_folder_id_from_url(google_drive_url)
        if not folder_id:
            raise ValueError("Invalid Google Drive folder URL")
        
        await self.bus.publish(IntegrationStatusEvent(
            status="Downloading transcripts from Google Drive", 
            session_id=self.session_id
        ))
        
        # Download transcript files from Google Drive
        transcript_files = await self._download_transcripts_from_drive(folder_id)
        
        await self.bus.publish(IntegrationStatusEvent(
            status=f"Found {len(transcript_files)} transcript files", 
            session_id=self.session_id
        ))
        
        for transcript_file in transcript_files:
            await self.bus.publish(IntegrationStatusEvent(
                status="Processing transcript", 
                current_file=transcript_file['file_name'],
                session_id=self.session_id
            ))
            
            await self._process_transcript(transcript_file)
        
        # Generate SQL statements
        sql_statements = self._generate_sql_statements()
        
        await self.bus.publish(IntegrationResultEvent(
            meetings_processed=len(self.meetings_data),
            members_identified=len(set([mm['member_id'] for mm in self.meeting_members_data])),
            projects_linked=len(set([mp['project_id'] for mp in self.meeting_projects_data])),
            session_id=self.session_id
        ))
        
        return {
            'meetings_processed': len(self.meetings_data),
            'members_identified': len(set([mm['member_id'] for mm in self.meeting_members_data])),
            'projects_linked': len(set([mp['project_id'] for mp in self.meeting_projects_data])),
            'sql_statements': sql_statements
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

    async def _process_transcript(self, transcript_file: Dict) -> None:
        """Process a single transcript file"""
        with open(transcript_file['local_path'], 'r', encoding='utf-8') as f:
            transcript_content = f.read()
        
        # Extract meeting information using GPT-4.1
        meeting_info = await self._extract_meeting_info(transcript_content, transcript_file)
        
        if meeting_info:
            self.meetings_data.append(meeting_info)
            
            # Add meeting members
            for member_name in meeting_info.get('members', []):
                member_id = self._find_member_id(member_name)
                if member_id:
                    self.meeting_members_data.append({
                        'meeting_id': meeting_info['meeting_id'],
                        'member_id': member_id
                    })
            
            # Use GPT's project identification
            gpt_identified_projects = meeting_info.get('projects', [])
            linked_project_ids = []
            
            for project_name in gpt_identified_projects:
                project_id = self._find_project_id(project_name)
                if project_id:
                    linked_project_ids.append(project_id)
                    print(f"Linked project '{project_name}' (ID: {project_id}) to meeting {meeting_info['meeting_id']}")
                else:
                    print(f"Warning: GPT identified project '{project_name}' but couldn't find matching project ID")
            
            # If GPT didn't identify any projects, use fallback
            if not linked_project_ids:
                print(f"GPT didn't identify any projects for meeting {meeting_info['meeting_id']}, using fallback")
                # Link to first available project as fallback
                if self.projects:
                    first_project_id = list(self.projects.values())[0]['id']
                    linked_project_ids.append(first_project_id)
                    print(f"Fallback: Linked to project ID {first_project_id}")
            
            # Add the linked projects
            for project_id in linked_project_ids:
                self.meeting_projects_data.append({
                    'meeting_id': meeting_info['meeting_id'],
                    'project_id': project_id
                })

    async def _extract_meeting_info(self, transcript_content: str, transcript_file: Dict) -> Optional[Dict]:
        """Extract meeting information using GPT-4.1"""
        
        prompt = f"""
You are an expert at analyzing meeting transcripts and extracting structured information.

Available committee members:
{self._format_committee_members()}

Available projects (you MUST match at least 1 project from this list):
{self._format_projects()}

Please analyze the following meeting transcript and extract:
1. Meeting type (e.g., "Project Discussion", "Planning Meeting", "Review Meeting")
2. Meeting date (if mentioned, otherwise use today's date)
3. List of committee members who participated (match names exactly from the available list)
4. List of projects that are relevant to this meeting (MUST include at least 1 project from the available list)

IMPORTANT: You MUST match at least 1 project from the available projects list. Look for:
- Direct mentions of project names (Even's Marathon, Nathan's Web, PJ's Database)
- Keywords related to project descriptions
- Technical terms that relate to projects
- Even if the connection is weak, include at least 1 project

Transcript:
{transcript_content}

Return your response in this exact JSON format:
{{
    "meeting_type": "string",
    "date": "YYYY-MM-DD",
    "members": ["member1", "member2"],
    "projects": ["project1", "project2"]
}}
"""
        
        try:
            response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
            content = response.raw.choices[0].message.content or "{}"
            
            # Extract JSON from response
            import json
            meeting_info = json.loads(content)
            
            # Add meeting_id and transcript_link
            meeting_info['meeting_id'] = len(self.meetings_data) + 1
            meeting_info['transcript_link'] = transcript_file['drive_link']
            meeting_info['meeting_summary'] = ""  # Leave blank for now
            
            # Ensure projects field exists (even if empty)
            if 'projects' not in meeting_info:
                meeting_info['projects'] = []
            
            return meeting_info
        except Exception as e:
            print(f"Error processing transcript {transcript_file['file_name']}: {e}")
            return None

    def _format_committee_members(self) -> str:
        """Format committee members for prompt"""
        return "\n".join([f"- {member['full_name']}" for member in self.committee_members.values()])

    def _format_projects(self) -> str:
        """Format projects for prompt"""
        return "\n".join([f"- {project['name']}: {project['summary']}" for project in self.projects.values()])

    def _format_projects_detailed(self) -> str:
        """Format projects with detailed information for better GPT analysis"""
        detailed_projects = []
        for project_name, project_info in self.projects.items():
            summary = project_info['summary']
            # Extract key terms for each project
            key_terms = self._extract_key_terms(summary)
            detailed_projects.append(
                f"- {project_info['name']} (ID: {project_info['id']}): {summary}\n"
                f"  Keywords: {', '.join(key_terms)}\n"
                f"  Related terms: {self._get_related_terms(project_name, summary)}"
            )
        return "\n\n".join(detailed_projects)

    def _get_related_terms(self, project_name: str, summary: str) -> str:
        """Get related terms for each project type"""
        summary_lower = summary.lower()
        if 'marathon' in summary_lower:
            return "marathon, running, race, charity, event, fundraising, sports, fitness, training"
        elif 'website' in summary_lower or 'web' in summary_lower:
            return "website, web, blog, personal, site, frontend, backend, development, coding, programming"
        elif 'database' in summary_lower:
            return "database, sql, data, schema, migration, backup, query, table, index, optimization"
        else:
            return "general, planning, discussion, review, update"

    def _find_member_id(self, member_name: str) -> Optional[int]:
        """Find member ID by name"""
        member_name_lower = member_name.lower()
        for name, member in self.committee_members.items():
            if member_name_lower in name or name in member_name_lower:
                return member['id']
        return None

    def _find_project_id(self, project_name: str) -> Optional[int]:
        """Find project ID by name with flexible matching"""
        project_name_lower = project_name.lower().strip()
        
        # Direct name matching
        for name, project in self.projects.items():
            if project_name_lower in name or name in project_name_lower:
                return project['id']
        
        # Flexible matching for common variations
        if 'marathon' in project_name_lower or 'even' in project_name_lower:
            for name, project in self.projects.items():
                if 'marathon' in name.lower():
                    return project['id']
        
        if 'website' in project_name_lower or 'web' in project_name_lower or 'nathan' in project_name_lower:
            for name, project in self.projects.items():
                if 'web' in name.lower():
                    return project['id']
        
        if 'database' in project_name_lower or 'pj' in project_name_lower:
            for name, project in self.projects.items():
                if 'database' in name.lower():
                    return project['id']
        
        return None

    def _link_projects_by_keywords(self, transcript_content: str, gpt_identified_projects: List[str]) -> List[int]:
        """Aggressive project linking using multiple strategies"""
        linked_project_ids = set()
        transcript_lower = transcript_content.lower()
        
        # Strategy 1: Add projects identified by GPT
        for project_name in gpt_identified_projects:
            project_id = self._find_project_id(project_name)
            if project_id:
                linked_project_ids.add(project_id)
                print(f"Linked project '{project_name}' via GPT identification")
        
        # Strategy 2: Aggressive keyword matching
        for project_name, project_info in self.projects.items():
            project_id = project_info['id']
            project_summary = project_info['summary'].lower()
            
            # Get all possible terms for this project
            key_terms = self._extract_key_terms(project_summary)
            related_terms = self._get_related_terms(project_name, project_summary).split(', ')
            
            # Check if ANY term appears in the transcript
            for term in key_terms + related_terms:
                if term.lower() in transcript_lower:
                    linked_project_ids.add(project_id)
                    print(f"Linked project '{project_name}' via keyword '{term}'")
                    break
        
        # Strategy 3: If no projects linked, link ALL projects (fallback)
        if not linked_project_ids:
            print("No projects linked via keywords, linking ALL projects as fallback")
            for project_info in self.projects.values():
                linked_project_ids.add(project_info['id'])
        
        # Strategy 4: Always include at least one project if we have meetings
        if self.meetings_data and not linked_project_ids:
            print("Fallback: Linking to first available project")
            if self.projects:
                first_project_id = list(self.projects.values())[0]['id']
                linked_project_ids.add(first_project_id)
        
        return list(linked_project_ids)

    def _extract_key_terms(self, project_summary: str) -> List[str]:
        """Extract comprehensive key terms from project summary for keyword matching"""
        # Remove common words and extract meaningful terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'led', 'by', 'for', 'research', 'project', 'system', 'developing', 'designing', 'implementing', 'organizing', 'personal'}
        
        # Split into words and filter
        words = re.findall(r'\b\w+\b', project_summary.lower())
        key_terms = [word for word in words if len(word) > 2 and word not in common_words]
        
        # Add comprehensive project-specific terms
        summary_lower = project_summary.lower()
        
        # Marathon project terms
        if 'marathon' in summary_lower or 'even' in summary_lower:
            key_terms.extend(['marathon', 'charity', 'event', 'running', 'race', 'even', 'organizing', 'fundraising', 'sports', 'fitness', 'training', 'athletic'])
        
        # Website project terms  
        if 'website' in summary_lower or 'web' in summary_lower or 'nathan' in summary_lower:
            key_terms.extend(['website', 'web', 'blog', 'personal', 'site', 'nathan', 'frontend', 'backend', 'development', 'coding', 'programming', 'html', 'css', 'javascript'])
        
        # Database project terms
        if 'database' in summary_lower or 'pj' in summary_lower:
            key_terms.extend(['database', 'sql', 'data', 'schema', 'migration', 'backup', 'pj', 'research', 'system', 'table', 'query', 'index', 'optimization', 'postgresql', 'mysql'])
        
        # Add person names as keywords
        if 'even' in summary_lower:
            key_terms.append('even')
        if 'nathan' in summary_lower:
            key_terms.append('nathan')
        if 'pj' in summary_lower:
            key_terms.append('pj')
        
        return list(set(key_terms))  # Remove duplicates

    def _generate_sql_statements(self) -> Dict[str, str]:
        """Generate SQL statements for the populated data"""
        
        # Generate meeting.sql with TRUNCATE
        meeting_sql = "TRUNCATE TABLE meeting;\n\n"
        meeting_sql += "INSERT INTO meeting (meeting_id, type, transcript_link, date, meeting_summary) VALUES\n"
        meeting_values = []
        for meeting in self.meetings_data:
            meeting_values.append(
                f"({meeting['meeting_id']}, '{meeting['meeting_type']}', '{meeting['transcript_link']}', '{meeting['date']}', '{meeting['meeting_summary']}')"
            )
        meeting_sql += ",\n".join(meeting_values) + ";"
        
        # Generate meeting_members.sql with TRUNCATE
        meeting_members_sql = "TRUNCATE TABLE meeting_members;\n\n"
        meeting_members_sql += "INSERT INTO meeting_members (meeting_id, member_id) VALUES\n"
        member_values = []
        for member in self.meeting_members_data:
            member_values.append(f"({member['meeting_id']}, {member['member_id']})")
        meeting_members_sql += ",\n".join(member_values) + ";"
        
        # Generate meeting_projects.sql with TRUNCATE
        meeting_projects_sql = "TRUNCATE TABLE meeting_projects;\n\n"
        meeting_projects_sql += "INSERT INTO meeting_projects (meeting_id, project_id) VALUES\n"
        project_values = []
        for project in self.meeting_projects_data:
            project_values.append(f"({project['meeting_id']}, {project['project_id']})")
        meeting_projects_sql += ",\n".join(project_values) + ";"
        
        return {
            'meeting.sql': meeting_sql,
            'meeting_members.sql': meeting_members_sql,
            'meeting_projects.sql': meeting_projects_sql
        }

    async def save_sql_files(self, sql_statements: Dict[str, str]) -> None:
        """Save SQL statements to files"""
        for filename, sql_content in sql_statements.items():
            filepath = os.path.join(DML_DIR, filename)
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(sql_content)
            print(f"Updated {filepath}")

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    
    model = Gpt41Mini(Providers.OPENAI)
    engine = TranscriptIntegratorEngine(model)
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(IntegrateTranscriptsCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(IntegrationStatusEvent)
    
    # Get Google Drive folder URL
    print("Transcript Integrator Engine")
    print("=" * 40)
    print("This engine will download transcripts from Google Drive and process them.")
    print("Make sure you have set up Google Drive API credentials (credentials.json)")
    print()
    
    google_drive_url = input("Enter Google Drive folder URL: ").strip()
    
    if not google_drive_url:
        print("No URL provided. Exiting.")
        return
    
    # Run the engine
    command = IntegrateTranscriptsCommand(google_drive_folder_url=google_drive_url)
    result = await engine.handle_command(command)
    
    if result.success:
        print("\n===== INTEGRATION RESULTS =====\n")
        data = result.result
        print(f"Meetings processed: {data['meetings_processed']}")
        print(f"Members identified: {data['members_identified']}")
        print(f"Projects linked: {data['projects_linked']}")
        
        # Show SQL preview
        print("\n===== SQL PREVIEW =====\n")
        for filename, sql_content in data['sql_statements'].items():
            print(f"--- {filename} ---")
            print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
            print()
        
        # Ask for confirmation
        confirm = input("Do the generated SQL statements look correct? (y/n): ").lower().strip()
        if confirm == 'y':
            await engine.save_sql_files(data['sql_statements'])
            print("SQL files updated successfully!")
        else:
            print("SQL files not updated.")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main()) 