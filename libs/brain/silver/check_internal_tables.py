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

class InternalTablesChecker:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def check_tables_exist(self, table_names: list[str]) -> dict[str, bool]:
        """Check if the specified tables exist in the silver schema"""
        async with self.async_session() as session:
            # Create placeholders for the table names
            placeholders = ','.join([f"'{name}'" for name in table_names])
            
            query = text(f"""
                SELECT table_name, 
                       CASE WHEN table_name IS NOT NULL THEN true ELSE false END as exists
                FROM information_schema.tables 
                WHERE table_schema = 'silver' 
                AND table_name IN ({placeholders})
            """)
            
            result = await session.execute(query)
            existing_tables = {row.table_name: row.exists for row in result.fetchall()}
            
            # Create result dict with all requested tables
            table_status = {}
            for table_name in table_names:
                table_status[table_name] = existing_tables.get(table_name, False)
            
            return table_status

    async def check_internal_tables(self):
        """Check if the 4 internal text channel tables exist"""
        tables_to_check = [
            'internal_text_channel_messages',
            'internal_text_chnl_msg_convo_member', 
            'internal_text_chnl_convo_members',
            'internal_text_channel_convos'
        ]
        
        print("🔍 Checking Internal Text Channel Tables")
        print("=" * 50)
        
        try:
            table_status = await self.check_tables_exist(tables_to_check)
            
            print("Table Status:")
            print("-" * 30)
            for table_name, exists in table_status.items():
                status_icon = "✅" if exists else "❌"
                print(f"{status_icon} {table_name}: {'EXISTS' if exists else 'MISSING'}")
            
            print(f"\nSummary:")
            existing_count = sum(table_status.values())
            total_count = len(tables_to_check)
            print(f"📊 {existing_count}/{total_count} tables exist")
            
            if existing_count == total_count:
                print("🎉 All tables are present!")
            elif existing_count == 0:
                print("⚠️  No tables found - they may need to be created")
            else:
                print("⚠️  Some tables are missing")
                
        except Exception as e:
            logger.error(f"Error checking tables: {e}")
            print(f"❌ Error: {e}")

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    checker = InternalTablesChecker()
    try:
        await checker.check_internal_tables()
    finally:
        await checker.close()

if __name__ == "__main__":
    asyncio.run(main()) 