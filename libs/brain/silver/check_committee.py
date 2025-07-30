import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../../../.env')
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

async def check_committee():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT member_id, name FROM silver.committee ORDER BY member_id'))
        rows = result.fetchall()
        
        print("Committee members:")
        print("-" * 30)
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}")
        
        print(f"\nTotal members: {len(rows)}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_committee()) 