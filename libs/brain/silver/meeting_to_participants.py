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

class MeetingToParticipants:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_participants_by_meeting_name(self, meeting_name: str) -> list:
        """Get all participants in a specific meeting"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT c.name as member_name, c.discord_id, c.notion_id, mm.type as participation_type
                FROM silver.meeting m
                JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
                JOIN silver.committee c ON mm.member_id = c.member_id
                WHERE m.name = :meeting_name
                ORDER BY c.name
            """), {"meeting_name": meeting_name})
            
            participants = result.fetchall()
            return participants

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Meeting to Participants Query")
        print("=" * 40)
        
        try:
            meeting_name = input("Enter meeting name: ").strip()
            if not meeting_name:
                print("❌ No meeting name provided")
                return
            
            participants = await self.get_participants_by_meeting_name(meeting_name)
            
            if not participants:
                print(f"❌ No participants found for meeting: {meeting_name}")
                return
            
            print(f"\n👥 Participants in meeting '{meeting_name}':")
            print("-" * 50)
            for i, participant in enumerate(participants, 1):
                print(f"{i}. {participant.member_name}")
                print(f"   Participation Type: {participant.participation_type}")
                if participant.discord_id:
                    print(f"   Discord ID: {participant.discord_id}")
                if participant.notion_id:
                    print(f"   Notion ID: {participant.notion_id}")
                print()
            
            print(f"Total participants: {len(participants)}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = MeetingToParticipants()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 