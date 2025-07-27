import os
import asyncio
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
import logging
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, select

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

# Enhanced summariser import
from . import enhanced_summariser

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Find the project root (ai-at-dscubed) dynamically
current_dir = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')):
    parent = os.path.dirname(current_dir)
    if parent == current_dir:
        raise FileNotFoundError("Could not find 'libs/brain/silver/DML' in any parent directory.")
    current_dir = parent

DML_DIR = os.path.join(current_dir, 'libs', 'brain', 'silver', 'DML')
print("DML_DIR being used:", DML_DIR)
SCOPES = ['https://www.googleapis.com/auth/drive']
Base = declarative_base()

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ensure the DATABASE_URL uses an async driver (asyncpg for PostgreSQL)
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    # Convert to asyncpg driver if not already
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    # Optionally, warn if the user is not using asyncpg
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

# Paths
committee_file = os.path.join(DML_DIR, 'committee.sql')
project_file = os.path.join(DML_DIR, 'project.sql')
print("Looking for committee.sql at:", committee_file, "Exists?", os.path.exists(committee_file))
print("Looking for project.sql at:", project_file, "Exists?", os.path.exists(project_file))
if os.path.exists(committee_file):
    with open(committee_file, 'r', encoding='utf-8') as f:
        print("First 5 lines of committee.sql:", [next(f) for _ in range(5)])
if os.path.exists(project_file):
    with open(project_file, 'r', encoding='utf-8') as f:
        print("First 5 lines of project.sql:", [next(f) for _ in range(5)])

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

class Meeting(Base):
    __tablename__ = 'meeting'
    __table_args__ = {'schema': 'silver'}
    meeting_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)
    meeting_summary = Column(Text)
    meeting_timestamp = Column(TIMESTAMP, nullable=False)
    ingestion_timestamp = Column(TIMESTAMP, nullable=False)

class MeetingMember(Base):
    __tablename__ = 'meeting_members'
    __table_args__ = {'schema': 'silver'}
    meeting_id = Column(Integer, ForeignKey('silver.meeting.meeting_id', ondelete='CASCADE'), primary_key=True)
    member_id = Column(Integer, ForeignKey('silver.committee.member_id', ondelete='CASCADE'), primary_key=True)
    type = Column(String(50), nullable=False)
    ingestion_timestamp = Column(TIMESTAMP, nullable=False)

class MeetingProject(Base):
    __tablename__ = 'meeting_projects'
    __table_args__ = {'schema': 'silver'}
    meeting_id = Column(Integer, ForeignKey('silver.meeting.meeting_id', ondelete='CASCADE'), primary_key=True)
    project_id = Column(Integer, ForeignKey('silver.project.project_id', ondelete='CASCADE'), primary_key=True)
    ingestion_timestamp = Column(TIMESTAMP, nullable=False)

class Committee(Base):
    __tablename__ = 'committee'
    __table_args__ = {'schema': 'silver'}
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

class Project(Base):
    __tablename__ = 'project'
    __table_args__ = {'schema': 'silver'}
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String)

class TranscriptIntegratorEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        """
        Initialize the transcript integrator engine, load context, and set up DB connection.
        """
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(os.urandom(8).hex())
        self.committee_members = None  # Will be loaded asynchronously
        self.projects = None           # Will be loaded asynchronously
        self.project_members = self._load_project_members()  # If you want to keep this from DML, that's fine
        self.drive_service = None
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def async_setup(self):
        self.committee_members = await self._load_committee_members_from_db()
        self.projects = await self._load_projects_from_db()

    async def _load_committee_members_from_db(self):
        members = {}
        async with self.async_session() as session:
            result = await session.execute(
                select(Committee.member_id, Committee.name)
            )
            for member_id, name in result.fetchall():
                members[name.lower()] = {'id': member_id, 'name': name}
        return members

    async def _load_projects_from_db(self):
        projects = {}
        async with self.async_session() as session:
            result = await session.execute(
                select(Project.project_id, Project.project_name)
            )
            for project_id, name in result.fetchall():
                projects[name.lower()] = {'id': project_id, 'name': name}
        return projects

    def _load_project_members(self) -> Dict[int, List[int]]:
        """
        Load project-member relationships from project_members.sql.
        """
        project_members: Dict[int, List[int]] = {}
        project_members_file = os.path.join(DML_DIR, 'project_members.sql')
        if os.path.exists(project_members_file):
            with open(project_members_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = re.findall(r"\((\d+), (\d+),", content)
                for project_id, member_id in matches:
                    project_id = int(project_id)
                    member_id = int(member_id)
                    if project_id not in project_members:
                        project_members[project_id] = []
                    project_members[project_id].append(member_id)
        return project_members

    async def handle_command(self, command: Command) -> CommandResult:
        """
        Entrypoint for llmgine command handling.
        """
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
            logger.error(f"Error in handle_command: {e}")
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    # === Google Drive File Selection ===
    async def list_and_select_files(self, folder_id: str) -> List[Dict]:
        """
        List all .txt files in the folder, order by date (parsed from filename, descending),
        show all files (including INGESTED), let user select by number, and return only selected files.
        """
        try:
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='text/plain'",
                fields="files(id, name, mimeType, webViewLink)"
            ).execute()
            files = results.get('files', [])
            if not files:
                logger.warning("No text files found in the specified folder.")
                return []
            # Parse date from filename and sort
            def parse_date_from_name(name: str) -> str:
                match = re.match(r'(?:INGESTED_)?(lecture|workshop)_([0-9]{4}-[0-9]{2}-[0-9]{2})', name.lower())
                if match:
                    return match.group(2)
                return '0000-00-00'
            files.sort(key=lambda f: parse_date_from_name(f['name']), reverse=True)
            print("\nAvailable transcript files:")
            for idx, file in enumerate(files, 1):
                print(f"{idx}. {file['name']}")
            print("\nSelect file(s) to process (comma-separated numbers, e.g. 1,3,5):")
            selection = input().strip()
            if not selection:
                print("No files selected. Exiting.")
                return []
            try:
                selected_indices = set(int(x.strip()) for x in selection.split(",") if x.strip())
            except Exception:
                print("Invalid selection. Exiting.")
                return []
            selected_files: List[Dict] = []
            for idx in selected_indices:
                if idx < 1 or idx > len(files):
                    print(f"Invalid selection: {idx}. Skipping.")
                    continue
                file = files[idx-1]
                if file['name'].startswith('INGESTED'):
                    print(f"Error: File '{file['name']}' has already been ingested. Skipping.")
                    continue
                selected_files.append(file)
            if not selected_files:
                print("No valid files selected. Exiting.")
                return []
            return selected_files
        except Exception as e:
            logger.error(f"Error listing/selecting files: {e}")
            return []

    async def rename_file_in_drive(self, file_id: str, old_name: str) -> None:
        """
        Rename a file in Google Drive to start with 'INGESTED_' if not already.
        """
        try:
            if old_name.startswith('INGESTED_'):
                return  # Already renamed
            new_name = f'INGESTED_{old_name}'
            self.drive_service.files().update(fileId=file_id, body={'name': new_name}).execute()
            logger.info(f"Renamed file '{old_name}' to '{new_name}' in Google Drive.")
        except Exception as e:
            logger.error(f"Failed to rename file '{old_name}' in Google Drive: {e}")

    # === Main Integration Workflow ===
    async def integrate_transcripts(self, google_drive_url: str) -> Dict[str, int]:
        """
        Main workflow: select files, process each, insert into DB, and rename in Drive.
        """
        await self.bus.publish(IntegrationStatusEvent(status="Starting transcript integration", session_id=self.session_id))
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ValueError("Google Drive API not available. Please install required packages.")
        await self.bus.publish(IntegrationStatusEvent(status="Authenticating with Google Drive", session_id=self.session_id))
        self.drive_service = await self._authenticate_google_drive()
        folder_id = self._extract_folder_id_from_url(google_drive_url)
        if not folder_id:
            raise ValueError("Invalid Google Drive folder URL")
        # List and let user select files
        selected_files = await self.list_and_select_files(folder_id)
        if not selected_files:
            return {'meetings_processed': 0, 'members_identified': 0, 'projects_linked': 0}
        await self.bus.publish(IntegrationStatusEvent(status=f"Selected {len(selected_files)} transcript files", session_id=self.session_id))
        meetings_processed = 0
        members_identified = set()
        projects_linked = set()
        temp_dir = tempfile.mkdtemp()
        for file in selected_files:
            file_id = file['id']
            file_name = file['name']
            web_view_link = file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            # Download file
            logger.info(f"Downloading: {file_name}")
            request = self.drive_service.files().get_media(fileId=file_id)
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Downloaded {int(status.progress() * 100)}% of {file_name}")
            await self.bus.publish(IntegrationStatusEvent(status="Processing transcript", current_file=file_name, session_id=self.session_id))
            try:
                # Parse meeting type and date from filename
                meeting_type, meeting_date = self._parse_filename(file_name)
                prompt = self._build_prompt(meeting_type, meeting_date, file_path)
                # Extract members/projects using GPT-4.1
                extraction = await self._extract_meeting_info(prompt)
                # Generate summary using enhanced_summariser
                summary = await enhanced_summariser.generate_summary_async(
                    file_path,
                    self.projects,
                    self.committee_members
                )
                print(f"[DEBUG] Summary returned by generate_summary_async for {file_name}:\n{summary}\n{'='*40}")
                # Insert into DB
                async with self.async_session() as session:
                    async with session.begin():
                        # Insert meeting
                        meeting = Meeting(
                            name=file_name,
                            type=meeting_type,
                            meeting_summary=summary,
                            meeting_timestamp=meeting_date,
                            ingestion_timestamp=datetime.utcnow()
                        )
                        session.add(meeting)
                        await session.flush()  # Get meeting_id
                        # Insert all members (no limit)
                        for member_id in extraction['member_ids']:
                            session.add(MeetingMember(
                                meeting_id=meeting.meeting_id,
                                member_id=member_id,
                                type=meeting_type,
                                ingestion_timestamp=datetime.utcnow()
                            ))
                            members_identified.add(member_id)
                        # Insert all projects (no limit)
                        for project_id in extraction['project_ids']:
                            session.add(MeetingProject(
                                meeting_id=meeting.meeting_id,
                                project_id=project_id,
                                ingestion_timestamp=datetime.utcnow()
                            ))
                            projects_linked.add(project_id)
                        await session.commit()
                        meetings_processed += 1
                # Rename file in Google Drive after successful processing
                await self.rename_file_in_drive(file_id, file_name)
            except Exception as e:
                logger.error(f"Error processing {file_name}: {e}")
        await self.bus.publish(IntegrationResultEvent(
            meetings_processed=meetings_processed,
            members_identified=len(members_identified),
            projects_linked=len(projects_linked),
            session_id=self.session_id
        ))
        return {
            'meetings_processed': meetings_processed,
            'members_identified': len(members_identified),
            'projects_linked': len(projects_linked)
        }

    def _parse_filename(self, filename: str) -> (str, datetime):
        """
        Parse meeting type and date from filename (e.g., workshop_05-07-2025_intro.txt).
        Expects date in dd-mm-yyyy format.
        """
        match = re.match(r"(lecture|workshop)_([0-9]{2}-[0-9]{2}-[0-9]{4})", filename.lower())
        if not match:
            raise ValueError(f"Filename {filename} does not match expected pattern (type_dd-mm-yyyy_...).")
        meeting_type = match.group(1)
        meeting_date = datetime.strptime(match.group(2), "%d-%m-%Y")
        return meeting_type, meeting_date

    def _build_prompt(self, meeting_type: str, meeting_date: datetime, transcript_path: str) -> str:
        """
        Build the GPT-4.1 prompt for member/project extraction, using the correct template for lectures/workshops.
        """
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_content = f.read()
        committee_context = "\n".join([f"- {m['name']}" for m in self.committee_members.values()])
        project_context = "\n".join([f"- {p['name']}" for p in self.projects.values()])
        if meeting_type == 'lecture':
            prompt = f"""
You are an expert at analyzing meeting transcripts and extracting structured information.

Available committee members:
{committee_context}

Available projects:
{project_context}

This is a lecture. Only one member (the speaker) is participating. Disregard anyone else mentioned.

Please analyze the following meeting transcript and extract:
1. List of committee members who participated (match names exactly from the available list; only the speaker should be included)
2. List of projects that are relevant to this meeting (MUST include at least 1 project from the available list)

IMPORTANT: You MUST match at least 1 project from the available projects list. Look for:
- Direct mentions of project names
- Keywords related to project descriptions
- Technical terms that relate to projects

Transcript:
{transcript_content}

Return your response in this exact JSON format:
{{
    "member_names": ["name1"],
    "project_names": ["project1"]
}}"""
        else:
            prompt = f"""
You are an expert at analyzing meeting transcripts and extracting structured information.

Available committee members:
{committee_context}

Available projects:
{project_context}

This is a workshop. Multiple members may participate.

Please analyze the following meeting transcript and extract:
1. List of committee members who participated (match names exactly from the available list)
2. List of projects that are relevant to this meeting (MUST include at least 1 project from the available list)

IMPORTANT: You MUST match at least 1 project from the available projects list. Look for:
- Direct mentions of project names
- Keywords related to project descriptions
- Technical terms that relate to projects

Transcript:
{transcript_content}

Return your response in this exact JSON format:
{{
    "member_names": ["name1", "name2"],
    "project_names": ["project1", "project2"]
}}"""
        return prompt

    async def _extract_meeting_info(self, prompt: str) -> Dict[str, List[int]]:
        """
        Use GPT-4.1 to extract member and project names, then map to IDs. Adds debug prints and fuzzy matching.
        """
        import difflib
        response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
        import json
        content = response.raw.choices[0].message.content or "{}"
        data = json.loads(content)
        print("LLM returned:", data)
        print("Committee members loaded:", list(self.committee_members.keys()))
        print("Projects loaded:", list(self.projects.keys()))
        member_ids = []
        for name in data.get('member_names', []):
            key = name.lower()
            if key in self.committee_members:
                member_ids.append(self.committee_members[key]['id'])
            else:
                # Fuzzy match fallback
                matches = difflib.get_close_matches(key, self.committee_members.keys(), n=1, cutoff=0.8)
                if matches:
                    print(f"Fuzzy matched member '{name}' to '{matches[0]}'")
                    member_ids.append(self.committee_members[matches[0]]['id'])
                else:
                    print(f"No match for member: {name}")
        project_ids = []
        for name in data.get('project_names', []):
            key = name.lower()
            if key in self.projects:
                project_ids.append(self.projects[key]['id'])
            else:
                # Fuzzy match fallback
                matches = difflib.get_close_matches(key, self.projects.keys(), n=1, cutoff=0.8)
                if matches:
                    print(f"Fuzzy matched project '{name}' to '{matches[0]}'")
                    project_ids.append(self.projects[matches[0]]['id'])
                else:
                    print(f"No match for project: {name}")
        return {'member_ids': member_ids, 'project_ids': project_ids}

    def _extract_folder_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract the folder ID from a Google Drive folder URL.
        """
        patterns = [r'/folders/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def _authenticate_google_drive(self):
        """
        Authenticate and return a Google Drive service client.
        """
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
        credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError("credentials.json not found")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        return build('drive', 'v3', credentials=creds)

    async def _download_transcripts_from_drive(self, folder_id: str) -> List[Dict]:
        transcript_files = []
        try:
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='text/plain'",
                fields="files(id, name, mimeType, webViewLink)"
            ).execute()
            files = results.get('files', [])
            if not files:
                logger.warning("No text files found in the specified folder.")
                return []
            temp_dir = tempfile.mkdtemp()
            for file in files:
                file_id = file['id']
                file_name = file['name']
                web_view_link = file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
                logger.info(f"Downloading: {file_name}")
                request = self.drive_service.files().get_media(fileId=file_id)
                file_path = os.path.join(temp_dir, file_name)
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            logger.info(f"Downloaded {int(status.progress() * 100)}% of {file_name}")
                transcript_files.append({
                    'local_path': file_path,
                    'drive_link': web_view_link,
                    'file_name': file_name
                })
            return transcript_files
        except Exception as e:
            logger.error(f"Error downloading files from Google Drive: {e}")
            return []

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    model = Gpt41Mini(Providers.OPENAI)
    engine = TranscriptIntegratorEngine(model)
    await engine.async_setup() # Added this line to load committee members
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(IntegrateTranscriptsCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(IntegrationStatusEvent)
    print("Transcript Integrator Engine")
    print("=" * 40)
    print("This engine will download transcripts from Google Drive, extract info, and insert into the database.")
    print("Make sure you have set up Google Drive API credentials (credentials.json)")
    print()
    google_drive_url = input("Enter Google Drive folder URL: ").strip()
    if not google_drive_url:
        print("No URL provided. Exiting.")
        return
    command = IntegrateTranscriptsCommand(google_drive_folder_url=google_drive_url)
    result = await engine.handle_command(command)
    if result.success:
        print("\n===== INTEGRATION RESULTS =====\n")
        data = result.result
        print(f"Meetings processed: {data['meetings_processed']}")
        print(f"Members identified: {data['members_identified']}")
        print(f"Projects linked: {data['projects_linked']}")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main()) 