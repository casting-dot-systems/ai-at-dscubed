import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeetingDBChecker:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def check_meetings_table(self):
        """Check all records in the meeting table"""
        async with self.async_session() as session:
            # Get total count
            count_result = await session.execute(text("SELECT COUNT(*) FROM silver.meeting"))
            total_count = count_result.scalar()
            print(f"\n=== MEETING TABLE OVERVIEW ===")
            print(f"Total meetings in database: {total_count}")
            
            if total_count == 0:
                print("No meetings found in the database.")
                return

            # Get all meetings with details
            result = await session.execute(text("""
                SELECT 
                    meeting_id,
                    name,
                    type,
                    meeting_summary,
                    meeting_timestamp,
                    ingestion_timestamp
                FROM silver.meeting 
                ORDER BY ingestion_timestamp DESC
            """))
            
            meetings = result.fetchall()
            
            print(f"\n=== RECENT MEETINGS (Last 10) ===")
            for i, meeting in enumerate(meetings[:10]):
                print(f"\n--- Meeting {i+1} ---")
                print(f"ID: {meeting.meeting_id}")
                print(f"Name: {meeting.name}")
                print(f"Type: {meeting.type}")
                print(f"Meeting Date: {meeting.meeting_timestamp}")
                print(f"Ingestion Date: {meeting.ingestion_timestamp}")
                print(f"Summary Length: {len(meeting.meeting_summary) if meeting.meeting_summary else 0} characters")
                
                if meeting.meeting_summary:
                    print(f"Summary Preview: {meeting.meeting_summary[:200]}...")
                    if len(meeting.meeting_summary) < 50:
                        print("⚠️  WARNING: Summary seems very short!")
                else:
                    print("❌ ERROR: No summary found!")
                
                print("-" * 50)

    async def check_meeting_members(self):
        """Check meeting members relationships"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    mm.meeting_id,
                    m.name as meeting_name,
                    c.name as member_name,
                    mm.type
                FROM silver.meeting_members mm
                JOIN silver.meeting m ON mm.meeting_id = m.meeting_id
                JOIN silver.committee c ON mm.member_id = c.member_id
                ORDER BY mm.meeting_id DESC
                LIMIT 20
            """))
            
            members = result.fetchall()
            
            print(f"\n=== MEETING MEMBERS (Last 20) ===")
            for member in members:
                print(f"Meeting: {member.meeting_name} | Member: {member.member_name} | Type: {member.type}")

    async def check_meeting_projects(self):
        """Check meeting projects relationships"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    mp.meeting_id,
                    m.name as meeting_name,
                    p.project_name,
                    mp.ingestion_timestamp
                FROM silver.meeting_projects mp
                JOIN silver.meeting m ON mp.meeting_id = m.meeting_id
                JOIN silver.project p ON mp.project_id = p.project_id
                ORDER BY mp.meeting_id DESC
                LIMIT 20
            """))
            
            projects = result.fetchall()
            
            print(f"\n=== MEETING PROJECTS (Last 20) ===")
            for project in projects:
                print(f"Meeting: {project.meeting_name} | Project: {project.project_name}")

    async def check_summary_statistics(self):
        """Check statistics about summaries"""
        async with self.async_session() as session:
            # Check for null summaries
            null_summary_result = await session.execute(text("""
                SELECT COUNT(*) FROM silver.meeting WHERE meeting_summary IS NULL
            """))
            null_count = null_summary_result.scalar()
            
            # Check for empty summaries
            empty_summary_result = await session.execute(text("""
                SELECT COUNT(*) FROM silver.meeting WHERE meeting_summary = ''
            """))
            empty_count = empty_summary_result.scalar()
            
            # Check for very short summaries (less than 50 characters)
            short_summary_result = await session.execute(text("""
                SELECT COUNT(*) FROM silver.meeting WHERE LENGTH(meeting_summary) < 50
            """))
            short_count = short_summary_result.scalar()
            
            # Get average summary length
            avg_length_result = await session.execute(text("""
                SELECT AVG(LENGTH(meeting_summary)) FROM silver.meeting WHERE meeting_summary IS NOT NULL
            """))
            avg_length = avg_length_result.scalar()
            
            print(f"\n=== SUMMARY STATISTICS ===")
            print(f"Total meetings: {await self.get_total_meetings()}")
            print(f"Null summaries: {null_count}")
            print(f"Empty summaries: {empty_count}")
            print(f"Short summaries (<50 chars): {short_count}")
            print(f"Average summary length: {avg_length:.1f} characters")
            
            if null_count > 0 or empty_count > 0:
                print("⚠️  WARNING: Found meetings without summaries!")
            if short_count > 0:
                print("⚠️  WARNING: Found meetings with very short summaries!")

    async def get_total_meetings(self) -> int:
        """Get total number of meetings"""
        async with self.async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM silver.meeting"))
            return result.scalar()

    async def check_recent_meeting_details(self, limit: int = 5):
        """Get detailed information about the most recent meetings"""
        async with self.async_session() as session:
            result = await session.execute(text(f"""
                SELECT 
                    meeting_id,
                    name,
                    type,
                    meeting_summary,
                    meeting_timestamp,
                    ingestion_timestamp,
                    LENGTH(meeting_summary) as summary_length
                FROM silver.meeting 
                ORDER BY ingestion_timestamp DESC
                LIMIT {limit}
            """))
            
            meetings = result.fetchall()
            
            print(f"\n=== DETAILED RECENT MEETINGS ===")
            for meeting in meetings:
                print(f"\n{'='*60}")
                print(f"Meeting ID: {meeting.meeting_id}")
                print(f"Name: {meeting.name}")
                print(f"Type: {meeting.type}")
                print(f"Meeting Date: {meeting.meeting_timestamp}")
                print(f"Ingestion Date: {meeting.ingestion_timestamp}")
                print(f"Summary Length: {meeting.summary_length} characters")
                print(f"\nFULL SUMMARY:")
                print(f"{'='*40}")
                if meeting.meeting_summary:
                    print(meeting.meeting_summary)
                else:
                    print("❌ NO SUMMARY FOUND")
                print(f"{'='*40}")

    async def run_full_check(self):
        """Run all checks"""
        print("🔍 Checking meeting table in database...")
        print(f"Database URL: {DATABASE_URL}")
        
        try:
            await self.check_meetings_table()
            await self.check_summary_statistics()
            await self.check_meeting_members()
            await self.check_meeting_projects()
            await self.check_recent_meeting_details()
            
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            print(f"❌ Error: {e}")

async def main():
    checker = MeetingDBChecker()
    await checker.run_full_check()

if __name__ == "__main__":
    asyncio.run(main()) 