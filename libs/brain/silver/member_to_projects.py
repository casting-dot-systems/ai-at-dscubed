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

class MemberToProjects:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_projects_by_member_name(self, member_name: str) -> list:
        """Get all projects a committee member is involved in"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT p.project_name, pm.ingestion_timestamp
                FROM silver.committee c
                JOIN silver.project_members pm ON c.member_id = pm.member_id
                JOIN silver.project p ON pm.project_id = p.project_id
                WHERE c.name = :member_name
                ORDER BY p.project_name
            """), {"member_name": member_name})
            
            projects = result.fetchall()
            return projects

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Member to Projects Query")
        print("=" * 40)
        
        try:
            member_name = input("Enter member name: ").strip()
            if not member_name:
                print("❌ No member name provided")
                return
            
            projects = await self.get_projects_by_member_name(member_name)
            
            if not projects:
                print(f"❌ No projects found for member: {member_name}")
                return
            
            print(f"\n📋 Projects for member '{member_name}':")
            print("-" * 50)
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project.project_name}")
                print(f"   Added to project: {project.ingestion_timestamp}")
                print()
            
            print(f"Total projects found: {len(projects)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = MemberToProjects()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 