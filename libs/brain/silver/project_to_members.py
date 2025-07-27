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

class ProjectToMembers:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_members_by_project_name(self, project_name: str) -> list:
        """Get all committee members working on a specific project"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT c.name as member_name, c.discord_id, c.notion_id, pm.ingestion_timestamp
                FROM silver.project p
                JOIN silver.project_members pm ON p.project_id = pm.project_id
                JOIN silver.committee c ON pm.member_id = c.member_id
                WHERE p.project_name = :project_name
                ORDER BY c.name
            """), {"project_name": project_name})
            
            members = result.fetchall()
            return members

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Project to Members Query")
        print("=" * 40)
        
        try:
            project_name = input("Enter project name: ").strip()
            if not project_name:
                print("❌ No project name provided")
                return
            
            members = await self.get_members_by_project_name(project_name)
            
            if not members:
                print(f"❌ No members found for project: {project_name}")
                return
            
            print(f"\n👥 Members working on project '{project_name}':")
            print("-" * 50)
            for i, member in enumerate(members, 1):
                print(f"{i}. {member.member_name}")
                if member.discord_id:
                    print(f"   Discord ID: {member.discord_id}")
                if member.notion_id:
                    print(f"   Notion ID: {member.notion_id}")
                print(f"   Added to project: {member.ingestion_timestamp}")
                print()
            
            print(f"Total members found: {len(members)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = ProjectToMembers()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 