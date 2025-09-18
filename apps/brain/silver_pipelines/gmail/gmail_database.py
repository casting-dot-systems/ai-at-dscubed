# test code for connection to database
import os
import asyncio
import re
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
import logging
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, select, JSON, true
from sqlalchemy.sql import func

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Create the declarative base
Base = declarative_base()

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))
DATABASE_URL = os.getenv('DATABASE_URL')

# Ensure the DATABASE_URL uses an async driver (asyncpg for PostgreSQL)
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    # Convert to asyncpg driver if not already
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    # Optionally, warn if the user is not using asyncpg
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)


# Emails Table
class Thread(Base):
    __tablename__ = 'thread'
    __table_args__ = {'schema': 'silver'}
    primary_id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(100), unique = True, nullable=False)
    email_address = Column(String(50), nullable=False)
    name = Column(String(50), nullable=True) # change to true?
    conversation = Column(JSON, nullable=False) # For example: ["user", "This is the text that they reply with", "Time that the email was sent"]
    ingestion_timestamp = Column(
        TIMESTAMP(timezone=True),          # <-- timestamptz
        nullable=False,
        server_default=func.now(),         # let DB set it if you omit in INSERT
    )

# Fix
@dataclass
class IntegrationStatusEvent(Event):
    status: str = ""
    current_file: str = ""


## Fix
@dataclass
class IntegrationResultEvent(Event):
    threads_processed:int = 0

#class CalendarEvent(Base):
#    __tablename__ = 'calendar_events'
#    __table_args__ = {'schema': 'silver'}
#    event_id = Column(Integer, primary_key=True, autoincrement=True)
#    event_name = Column(String(50), nullable=False)
#    description = Column(Text)
#    location = Column(String(50))
#    event_starttime = Column(TIMESTAMP, nullable=False)
#    event_endtime = Column(TIMESTAMP, nullable=False)
#    ingestion_timestamp = Column(TIMESTAMP, nullable=False)


class EmailEngine:
    def __init__(self, session_id: Optional[SessionID] = None):
        """
        Initialize the email uploader engine, load context, and set up DB connection.
        """
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(os.urandom(8).hex())
        self.emails = None  # Will be loaded asynchronously
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def _load_threads_from_db(self):
        """Load emails from the database"""
        threads = {}
        async with self.async_session() as session:
            result = await session.execute(
                select(Thread.thread_id, Thread.email_address, Thread.name, Thread.conversation)
            )
            for thread_id, email_address, name, conversation in result.fetchall():
                threads[thread_id] = {'thread_id': thread_id, 'email_address':email_address,'name': name, 'conversation':conversation}
        return threads

    async def _add_new_thread(self, thread_id, email_address, name, conversation):
        """Add a completely new thread"""

        try:
            async with self.async_session() as session:
                async with session.begin():
                    # Insert thread
                    new_thread = Thread(
                        thread_id=thread_id,
                        email_address=email_address,
                        name=name,
                        conversation=conversation,
                        ingestion_timestamp=datetime.now(timezone.utc)
                    )
                    session.add(new_thread)
                    await session.flush()  # Get thread_id                        
                    await session.commit()
        except Exception as e:
            logger.error(f"Error processing thread with {email_address}: {e}")

        # Fix
        await self.bus.publish(IntegrationResultEvent(
            threads_processed=1,
            session_id=self.session_id
        ))
    
    async def _update_existing_thread(self, conversation, thread_id):
        """Add a new email to an existing thread"""
        try:
            async with self.async_session() as session:
                existing = (await session.execute(
                    select(Thread).where(Thread.thread_id == thread_id)
                )).scalar_one_or_none()

                if not existing:
                    raise ValueError(f"Thread {thread_id} not found")

                convo = list(existing.conversation or [])
                convo.extend(conversation)
                existing.conversation = convo

                await session.commit()

        except Exception as e:
            logger.error(f"Error updating thread: {e}")

    async def ingest_email(self, thread_id, email_address, name, conversation):
        """Ingest an email into the database"""
        # Load existing threads
        threads = await self._load_threads_from_db()
        
        # Check if thread already exists
        thread_key = thread_id
        if thread_key in threads:
            print(f"Thread found for {thread_id}")
            # Update existing thread
            await self._update_existing_thread(conversation, thread_key)
        else:
            print(f"No thread found for {thread_id}, creating new thread")
            # Create new thread
            await self._add_new_thread(thread_id, email_address, name, conversation)

if __name__=="__main__":
    client=EmailEngine()
    conversation = [
        {
            "Role":"Agent",
            "Message": "Test Message 2",
            "Timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    # Note: threadId is from gmail
    result = asyncio.run(client.ingest_email("10927e", "test_email@dscubed.org.au", "Test name", conversation))

    # why thread_id not unique
        

    


        






