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

class DummyDataIngester:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def ingest_dummy_data(self):
        """Ingest dummy data from the SQL file"""
        try:
            # Read the dummy data SQL file
            sql_file_path = os.path.join(os.path.dirname(__file__), 'dummy_data.sql')
            
            if not os.path.exists(sql_file_path):
                logger.error(f"❌ SQL file not found: {sql_file_path}")
                return False
            
            with open(sql_file_path, 'r') as file:
                sql_content = file.read()
            
            # Split the content by semicolon to separate SQL commands
            sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
            
            print("📥 Ingesting Dummy Data")
            print("=" * 40)
            
            # First, check if committee data exists
            async with self.async_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM silver.committee"))
                committee_count = result.scalar()
                print(f"Found {committee_count} committee members")
                
                if committee_count == 0:
                    print("❌ No committee members found. Please run the committee DML first.")
                    return False
            
            # Execute each command in its own transaction
            success_count = 0
            total_commands = len(sql_commands)
            
            for i, command in enumerate(sql_commands, 1):
                if command:  # Skip empty commands
                    try:
                        async with self.async_session() as session:
                            await session.execute(text(command))
                            await session.commit()
                            success_count += 1
                            print(f"✅ Executed command {i}/{total_commands}")
                    except Exception as e:
                        logger.error(f"❌ Error executing command {i}: {e}")
                        print(f"❌ Failed command {i}/{total_commands}")
                        # Continue with next command instead of stopping
            
            print(f"\nSummary:")
            print(f"📊 {success_count}/{total_commands} commands executed successfully")
            
            if success_count == total_commands:
                print("🎉 All dummy data ingested successfully!")
                return True
            else:
                print("⚠️  Some commands failed")
                return False
                    
        except Exception as e:
            logger.error(f"❌ Error ingesting dummy data: {e}")
            return False

    async def verify_data_ingestion(self):
        """Verify that the data was ingested correctly"""
        try:
            async with self.async_session() as session:
                # Count total messages
                result = await session.execute(text("SELECT COUNT(*) as count FROM silver.internal_text_channel_messages"))
                total_messages = result.scalar()
                
                # Count messages by channel
                result = await session.execute(text("""
                    SELECT channel_id, COUNT(*) as count 
                    FROM silver.internal_text_channel_messages 
                    GROUP BY channel_id 
                    ORDER BY channel_id
                """))
                channel_counts = result.fetchall()
                
                print(f"\n📊 Data Verification:")
                print(f"Total messages: {total_messages}")
                print("Messages by channel:")
                for channel_id, count in channel_counts:
                    print(f"  Channel {channel_id}: {count} messages")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error verifying data: {e}")
            return False

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    ingester = DummyDataIngester()
    try:
        # Ingest the dummy data
        success = await ingester.ingest_dummy_data()
        
        if success:
            # Verify the data was ingested correctly
            await ingester.verify_data_ingestion()
        else:
            print("❌ Failed to ingest dummy data")
            
    finally:
        await ingester.close()

if __name__ == "__main__":
    asyncio.run(main()) 