import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any

# Add the apps/brain directory to the path so we can import pipeline.py
sys.path.append(str(Path(__file__).parent.parent.parent))

from pipeline import Pipeline

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseTransformer:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        # Initialize pipeline for silver schema operations
        self.pipeline = Pipeline(schema='silver')
        
    async def get_committee_mapping(self) -> Dict[str, int]:
        """Get mapping from Discord user ID (string) to committee member ID (int)"""
        async with self.async_session() as session:
            result = await session.execute(text("""
                SELECT discord_id, member_id 
                FROM silver.committee 
                WHERE discord_id IS NOT NULL
            """))
            mapping = {str(row.discord_id): row.member_id for row in result.fetchall()}
            logger.info(f"Loaded {len(mapping)} committee member mappings")
            return mapping
    
    async def close(self):
        """Close the database engine"""
        await self.engine.dispose()