# test code for connection to database
import os
import asyncio
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
import logging
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, select

load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver (asyncpg for PostgreSQL)
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    # Convert to asyncpg driver if not already
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    # Optionally, warn if the user is not using asyncpg
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)


# Emails Table - copy for other tables
class Emails(Base):
    __tablename__ = 'emails'
    __table_args__ = {'schema': 'silver'}
    email_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)
    email_summary = Column(Text)
    email_timestamp = Column(TIMESTAMP, nullable=False)
    ingestion_timestamp = Column(TIMESTAMP, nullable=False)

class EmailUploadEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        """
        Initialize the email uploader engine, load context, and set up DB connection.
        """
        self.model = model  # could delete
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(os.urandom(8).hex())
        self.emails = None  # Will be loaded asynchronously
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

