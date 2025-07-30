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

class MessagesDataChecker:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def check_messages_data(self):
        """Check the data in the internal_text_channel_messages table"""
        try:
            async with self.async_session() as session:
                # Get total count
                result = await session.execute(text("SELECT COUNT(*) FROM silver.internal_text_channel_messages"))
                total_count = result.scalar()
                
                print("📊 Internal Text Channel Messages Data Check")
                print("=" * 60)
                print(f"Total messages: {total_count}")
                
                # Get count by channel
                result = await session.execute(text("""
                    SELECT channel_id, COUNT(*) as count 
                    FROM silver.internal_text_channel_messages 
                    GROUP BY channel_id 
                    ORDER BY channel_id
                """))
                channel_counts = result.fetchall()
                
                print(f"\n📈 Messages by Channel:")
                print("-" * 30)
                for channel_id, count in channel_counts:
                    print(f"Channel {channel_id}: {count} messages")
                
                # Get count by member
                result = await session.execute(text("""
                    SELECT member_id, COUNT(*) as count 
                    FROM silver.internal_text_channel_messages 
                    GROUP BY member_id 
                    ORDER BY count DESC
                    LIMIT 10
                """))
                member_counts = result.fetchall()
                
                print(f"\n👥 Top 10 Most Active Members:")
                print("-" * 35)
                for member_id, count in member_counts:
                    print(f"Member {member_id}: {count} messages")
                
                # Show sample messages from our dummy data (channels 1 and 3)
                print(f"\n💬 Sample Messages from Channels 1 & 3:")
                print("-" * 45)
                
                result = await session.execute(text("""
                    SELECT m.message_id, m.member_id, m.channel_id, m.message, m.date_created,
                           c.name as member_name
                    FROM silver.internal_text_channel_messages m
                    LEFT JOIN silver.committee c ON m.member_id = c.member_id
                    WHERE m.channel_id IN (1, 3)
                    ORDER BY m.channel_id, m.date_created
                    LIMIT 20
                """))
                
                messages = result.fetchall()
                
                current_channel = None
                for msg in messages:
                    if current_channel != msg.channel_id:
                        current_channel = msg.channel_id
                        print(f"\n--- Channel {msg.channel_id} ---")
                    
                    member_name = msg.member_name or f"Member {msg.member_id}"
                    print(f"[{msg.date_created.strftime('%Y-%m-%d %H:%M')}] {member_name}: {msg.message[:80]}{'...' if len(msg.message) > 80 else ''}")
                
                # Show conversation statistics
                print(f"\n📋 Conversation Statistics:")
                print("-" * 30)
                
                # Count conversations by time gaps (messages more than 1 hour apart)
                result = await session.execute(text("""
                    WITH time_gaps AS (
                        SELECT 
                            channel_id,
                            date_created,
                            LAG(date_created) OVER (PARTITION BY channel_id ORDER BY date_created) as prev_time
                        FROM silver.internal_text_channel_messages
                        WHERE channel_id IN (1, 3)
                    )
                    SELECT 
                        channel_id,
                        COUNT(*) as conversation_breaks
                    FROM time_gaps
                    WHERE prev_time IS NULL OR date_created - prev_time > INTERVAL '1 hour'
                    GROUP BY channel_id
                    ORDER BY channel_id
                """))
                
                conversation_breaks = result.fetchall()
                for channel_id, breaks in conversation_breaks:
                    conversations = breaks + 1  # Number of conversations = breaks + 1
                    print(f"Channel {channel_id}: ~{conversations} conversations detected")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error checking messages data: {e}")
            return False

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    checker = MessagesDataChecker()
    try:
        await checker.check_messages_data()
    finally:
        await checker.close()

if __name__ == "__main__":
    asyncio.run(main()) 