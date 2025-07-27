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

class DiscordToMeetings:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def get_meetings_by_discord_id(self, discord_id: int) -> list:
        """Get all meetings a Discord user participated in"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT DISTINCT m.name as meeting_name, m.type, m.meeting_timestamp
                FROM silver.meeting m
                JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
                JOIN silver.committee c ON mm.member_id = c.member_id
                WHERE c.discord_id = :discord_id
                ORDER BY m.meeting_timestamp DESC
            """), {"discord_id": discord_id})
            
            meetings = result.fetchall()
            return meetings

    async def run_query(self):
        """Main function to get user input and display results"""
        print("🔍 Discord ID to Meetings Query")
        print("=" * 40)
        
        try:
            discord_id = input("Enter Discord ID: ").strip()
            if not discord_id:
                print("❌ No Discord ID provided")
                return
            
            discord_id = int(discord_id)
            meetings = await self.get_meetings_by_discord_id(discord_id)
            
            if not meetings:
                print(f"❌ No meetings found for Discord ID: {discord_id}")
                return
            
            print(f"\n📋 Meetings for Discord ID {discord_id}:")
            print("-" * 50)
            for i, meeting in enumerate(meetings, 1):
                print(f"{i}. {meeting.meeting_name}")
                print(f"   Type: {meeting.type}")
                print(f"   Date: {meeting.meeting_timestamp}")
                print()
            
            print(f"Total meetings found: {len(meetings)}")
            
        except ValueError:
            print("❌ Invalid Discord ID. Please enter a valid number.")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"❌ Error: {e}")

async def main():
    query = DiscordToMeetings()
    await query.run_query()

if __name__ == "__main__":
    asyncio.run(main()) 