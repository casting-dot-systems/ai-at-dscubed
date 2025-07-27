import os
import asyncio
from dotenv import load_dotenv
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectToMeetings:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_meetings_by_project_name(self, project_name: str) -> list:
        """Get all meetings related to a specific project"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT m.name as meeting_name, m.type, m.meeting_timestamp, m.meeting_summary
                FROM silver.project p
                JOIN silver.meeting_projects mp ON p.project_id = mp.project_id
                JOIN silver.meeting m ON mp.meeting_id = m.meeting_id
                WHERE p.project_name = :project_name
                ORDER BY m.meeting_timestamp DESC
            """), {"project_name": project_name})
            
            meetings = result.fetchall()
            return meetings

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Project to Meetings Query")
        print("=" * 40)
        
        try:
            project_name = input("Enter project name: ").strip()
            if not project_name:
                print("❌ No project name provided")
                return
            
            meetings = await self.get_meetings_by_project_name(project_name)
            
            if not meetings:
                print(f"❌ No meetings found for project: {project_name}")
                return
            
            print(f"\n📋 Meetings related to project '{project_name}':")
            print("-" * 50)
            for i, meeting in enumerate(meetings, 1):
                print(f"{i}. {meeting.meeting_name}")
                print(f"   Type: {meeting.type}")
                print(f"   Date: {meeting.meeting_timestamp}")
                if meeting.meeting_summary:
                    summary_preview = meeting.meeting_summary[:100] + "..." if len(meeting.meeting_summary) > 100 else meeting.meeting_summary
                    print(f"   Summary Preview: {summary_preview}")
                print()
            
            print(f"Total meetings found: {len(meetings)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = ProjectToMeetings()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 