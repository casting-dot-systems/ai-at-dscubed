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

class TableCreator:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def create_tables(self):
        """Create the new tables"""
        ddl_files = [
            'internal_msg_convos.sql',
            'internal_msg_convo_members.sql', 
            'internal_msg_message_convo_members.sql',
            'internal_msg_message.sql'
        ]
        
        ddl_dir = os.path.join(os.path.dirname(__file__), 'DDL')
        
        print("🏗️  Creating New Tables")
        print("=" * 40)
        
        for ddl_file in ddl_files:
            file_path = os.path.join(ddl_dir, ddl_file)
            
            if not os.path.exists(file_path):
                logger.error(f"❌ DDL file not found: {file_path}")
                continue
                
            try:
                with open(file_path, 'r') as file:
                    sql_content = file.read()
                
                async with self.async_session() as session:
                    await session.execute(text(sql_content))
                    await session.commit()
                    print(f"✅ Created table from {ddl_file}")
                    
            except Exception as e:
                logger.error(f"❌ Error creating table from {ddl_file}: {e}")
                print(f"❌ Failed to create table from {ddl_file}")

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    creator = TableCreator()
    try:
        await creator.create_tables()
        print("\n🎉 Table creation completed!")
    finally:
        await creator.close()

if __name__ == "__main__":
    asyncio.run(main())

