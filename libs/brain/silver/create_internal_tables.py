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

class InternalTablesCreator:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def create_table_from_file(self, ddl_file_path: str, table_name: str):
        """Create a table from a DDL file"""
        try:
            with open(ddl_file_path, 'r') as file:
                ddl_content = file.read()
            
            # Split the content by semicolon to separate SQL commands
            sql_commands = [cmd.strip() for cmd in ddl_content.split(';') if cmd.strip()]
            
            async with self.async_session() as session:
                for command in sql_commands:
                    if command:  # Skip empty commands
                        await session.execute(text(command))
                await session.commit()
                logger.info(f"✅ Successfully created table: {table_name}")
                return True
        except Exception as e:
            logger.error(f"❌ Error creating table {table_name}: {e}")
            return False

    async def create_internal_tables(self):
        """Create the three missing internal text channel tables"""
        ddl_dir = os.path.join(os.path.dirname(__file__), 'DDL')
        
        # Tables must be created in dependency order due to foreign keys
        tables_to_create = [
            ('internal_text_channel_convos.sql', 'internal_text_channel_convos'),
            ('internal_text_chnl_convo_members.sql', 'internal_text_chnl_convo_members'),
            ('internal_text_chnl_msg_convo_member.sql', 'internal_text_chnl_msg_convo_member')
        ]
        
        print("🔨 Creating Internal Text Channel Tables")
        print("=" * 50)
        
        success_count = 0
        for ddl_file, table_name in tables_to_create:
            ddl_path = os.path.join(ddl_dir, ddl_file)
            if os.path.exists(ddl_path):
                print(f"Creating table: {table_name}")
                success = await self.create_table_from_file(ddl_path, table_name)
                if success:
                    success_count += 1
                else:
                    print(f"❌ Failed to create {table_name}, stopping execution")
                    break  # Stop if a table fails due to dependencies
            else:
                logger.error(f"❌ DDL file not found: {ddl_path}")
                break
        
        print(f"\nSummary:")
        print(f"📊 {success_count}/{len(tables_to_create)} tables created successfully")
        
        if success_count == len(tables_to_create):
            print("🎉 All tables created successfully!")
        else:
            print("⚠️  Some tables failed to create")

    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()

async def main():
    creator = InternalTablesCreator()
    try:
        await creator.create_internal_tables()
    finally:
        await creator.close()

if __name__ == "__main__":
    asyncio.run(main()) 