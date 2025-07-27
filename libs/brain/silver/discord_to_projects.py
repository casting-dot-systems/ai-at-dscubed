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

class DiscordToProjects:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_projects_by_discord_id(self, discord_id: int) -> list:
        """Get all projects a Discord user is involved in"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT p.project_name, pm.ingestion_timestamp
                FROM silver.committee c
                JOIN silver.project_members pm ON c.member_id = pm.member_id
                JOIN silver.project p ON pm.project_id = p.project_id
                WHERE c.discord_id = :discord_id
                ORDER BY p.project_name
            """), {"discord_id": discord_id})
            
            projects = result.fetchall()
            return projects

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Discord ID to Projects Query")
        print("=" * 40)
        
        try:
            discord_id = input("Enter Discord ID: ").strip()
            if not discord_id:
                print("❌ No Discord ID provided")
                return
            
            discord_id = int(discord_id)
            projects = await self.get_projects_by_discord_id(discord_id)
            
            if not projects:
                print(f"❌ No projects found for Discord ID: {discord_id}")
                return
            
            print(f"\n📋 Projects for Discord ID {discord_id}:")
            print("-" * 50)
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project.project_name}")
                print(f"   Added to project: {project.ingestion_timestamp}")
                print()
            
            print(f"Total projects found: {len(projects)}")
            
        except ValueError:
            print("❌ Invalid Discord ID. Please enter a valid number.")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = DiscordToProjects()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 