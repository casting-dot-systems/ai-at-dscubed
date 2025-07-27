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

class NotionToMeetings:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_meetings_by_notion_id(self, notion_id: str) -> list:
        """Get all meetings a Notion user participated in"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT DISTINCT m.name as meeting_name, m.type, m.meeting_timestamp
                FROM silver.meeting m
                JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
                JOIN silver.committee c ON mm.member_id = c.member_id
                WHERE c.notion_id = :notion_id
                ORDER BY m.meeting_timestamp DESC
            """), {"notion_id": notion_id})
            
            meetings = result.fetchall()
            return meetings

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Notion ID to Meetings Query")
        print("=" * 40)
        
        try:
            notion_id = input("Enter Notion ID: ").strip()
            if not notion_id:
                print("❌ No Notion ID provided")
                return
            
            meetings = await self.get_meetings_by_notion_id(notion_id)
            
            if not meetings:
                print(f"❌ No meetings found for Notion ID: {notion_id}")
                return
            
            print(f"\n📋 Meetings for Notion ID {notion_id}:")
            print("-" * 50)
            for i, meeting in enumerate(meetings, 1):
                print(f"{i}. {meeting.meeting_name}")
                print(f"   Type: {meeting.type}")
                print(f"   Date: {meeting.meeting_timestamp}")
                print()
            
            print(f"Total meetings found: {len(meetings)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = NotionToMeetings()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 