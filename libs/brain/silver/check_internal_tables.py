import os
import asyncio
from dotenv import load_dotenv

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

async def check_tables():
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    try:
        async with async_session() as session:
            # Check internal_text_channel_convos
            print("=== internal_text_channel_convos ===")
            result = await session.execute(text("SELECT * FROM silver.internal_text_channel_convos"))
            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"convo_id: {row.convo_id}, summary: {row.convo_summary}, timestamp: {row.ingestion_timestamp}")
            else:
                print("No data found")
            print()
            
            # Check internal_text_chnl_convo_members
            print("=== internal_text_chnl_convo_members ===")
            result = await session.execute(text("SELECT * FROM silver.internal_text_chnl_convo_members"))
            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"convo_id: {row.convo_id}, member_id: {row.member_id}, timestamp: {row.ingestion_timestamp}")
            else:
                print("No data found")
            print()
            
            # Check internal_text_chnl_msg_convo_member
            print("=== internal_text_chnl_msg_convo_member ===")
            result = await session.execute(text("SELECT * FROM silver.internal_text_chnl_msg_convo_member"))
            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"message_id: {row.message_id}, member_id: {row.member_id}, convo_id: {row.convo_id}, timestamp: {row.ingestion_timestamp}")
            else:
                print("No data found")
            print()
            
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_tables()) 