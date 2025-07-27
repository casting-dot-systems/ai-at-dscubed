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

class MeetingToProjects:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_projects_by_meeting_name(self, meeting_name: str) -> list:
        """Get all projects discussed in a specific meeting"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT p.project_name, mp.ingestion_timestamp
                FROM silver.meeting m
                JOIN silver.meeting_projects mp ON m.meeting_id = mp.meeting_id
                JOIN silver.project p ON mp.project_id = p.project_id
                WHERE m.name = :meeting_name
                ORDER BY p.project_name
            """), {"meeting_name": meeting_name})
            
            projects = result.fetchall()
            return projects

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Meeting to Projects Query")
        print("=" * 40)
        
        try:
            meeting_name = input("Enter meeting name: ").strip()
            if not meeting_name:
                print("❌ No meeting name provided")
                return
            
            projects = await self.get_projects_by_meeting_name(meeting_name)
            
            if not projects:
                print(f"❌ No projects found for meeting: {meeting_name}")
                return
            
            print(f"\n📋 Projects discussed in meeting '{meeting_name}':")
            print("-" * 50)
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project.project_name}")
                print(f"   Linked to meeting: {project.ingestion_timestamp}")
                print()
            
            print(f"Total projects found: {len(projects)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = MeetingToProjects()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 