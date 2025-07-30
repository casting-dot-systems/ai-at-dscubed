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

class TableStructureChecker:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def check_table_structure(self):
        """Check the structure of the internal_text_channel_messages table"""
        try:
            async with self.async_session() as session:
                # Get column information
                result = await session.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'silver' 
                    AND table_name = 'internal_text_channel_messages'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                
                print("📋 Table Structure: silver.internal_text_channel_messages")
                print("=" * 60)
                print(f"{'Column Name':<20} {'Data Type':<15} {'Nullable':<10} {'Default'}")
                print("-" * 60)
                
                for column in columns:
                    print(f"{column.column_name:<20} {column.data_type:<15} {column.is_nullable:<10} {column.column_default or 'NULL'}")
                
                print(f"\nTotal columns: {len(columns)}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error checking table structure: {e}")
            return False

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    checker = TableStructureChecker()
    try:
        await checker.check_table_structure()
    finally:
        await checker.close()

if __name__ == "__main__":
    asyncio.run(main()) 