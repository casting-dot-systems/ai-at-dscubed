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
            sql_file_path = os.path.join(os.path.dirname(__file__), 'realistic_dummy_data_v2.sql')
            
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
                result = await session.execute(text("SELECT COUNT(*) as count FROM silver.internal_msg_message"))
                total_messages = result.scalar()
                
                # Count messages by component
                result = await session.execute(text("""
                    SELECT component_id, COUNT(*) as count 
                    FROM silver.internal_msg_message 
                    GROUP BY component_id 
                    ORDER BY component_id
                """))
                component_counts = result.fetchall()
                
                print(f"\n📊 Data Verification:")
                print(f"Total messages: {total_messages}")
                print("Messages by component:")
                for component_id, count in component_counts:
                    print(f"  Component {component_id}: {count} messages")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error verifying data: {e}")
            return False

    async def check_existing_data(self):
        """Check what data already exists in the database"""
        try:
            async with self.async_session() as session:
                # Count total messages
                result = await session.execute(text("SELECT COUNT(*) as count FROM silver.internal_msg_message"))
                total_messages = result.scalar()
                
                # Count messages by component
                result = await session.execute(text("""
                    SELECT component_id, COUNT(*) as count 
                    FROM silver.internal_msg_message 
                    GROUP BY component_id 
                    ORDER BY component_id
                """))
                component_counts = result.fetchall()
                
                print(f"\n📊 Current Database State:")
                print(f"Total messages: {total_messages}")
                print("Messages by component:")
                for component_id, count in component_counts:
                    print(f"  Component {component_id}: {count} messages")
                
                return total_messages > 0
                
        except Exception as e:
            logger.error(f"❌ Error checking existing data: {e}")
            return False

    async def clear_existing_data(self):
        """Clear all existing data from the table"""
        try:
            async with self.async_session() as session:
                await session.execute(text("DELETE FROM silver.internal_msg_message"))
                await session.commit()
                print("🗑️  Cleared existing data from internal_msg_message table")
                return True
        except Exception as e:
            logger.error(f"❌ Error clearing data: {e}")
            return False

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    ingester = DummyDataIngester()
    try:
        # Check existing data first
        has_existing_data = await ingester.check_existing_data()
        
        if has_existing_data:
            print("\n⚠️  Existing data found! This may cause duplicate key errors.")
            response = input("Do you want to clear existing data before ingesting? (y/N): ").strip().lower()
            if response == 'y':
                await ingester.clear_existing_data()
            else:
                print("Continuing without clearing data...")
        
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