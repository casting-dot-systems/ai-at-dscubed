from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
import asyncio
from dotenv import load_dotenv
import os
import json
import logging

from sqlalchemy import String, Text, TIMESTAMP, func, ForeignKey, UniqueConstraint
from sqlalchemy import Column, Integer, select, JSON, true
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, sessionmaker
from sqlalchemy.dialects.postgresql import insert, ENUM
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

Base = declarative_base()

sender_type = ENUM("user", "agent", name="sender_type", create_type=False)

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

logger = logging.getLogger(__name__)

# Ensure the DATABASE_URL uses an async driver (asyncpg for PostgreSQL)
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    # Convert to asyncpg driver if not already
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    # Optionally, warn if the user is not using asyncpg
elif DATABASE_URL and DATABASE_URL.startswith('postgresql+psycopg2://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)

###### FIX THIS
class EmailUsers(Base):
    __tablename__ = "email_users"
    users_email_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class Emails(Base):
    __tablename__ = "emails"
    thread_id = Column(Text, primary_key=True, nullable=False)
    email_id = Column(Text, nullable=False)
    user_email = Column(
        Text,
        ForeignKey("email_users.email", ondelete="CASCADE"),
        nullable=False,
    )
    sender = Column(sender_type, nullable=False)
    body = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

class DatabaseManager:
    def __init__(self) -> None:
        self.emails = None  # Will be loaded asynchronously
        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def store_message(self, user_data: Dict[str, Any], message_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Stores a user and their associated message in the database.
        
        Args:
            user_data (dict): A dictionary with 'email' and 'name' keys.
                Example: {"email": "user@example.com", "name": "John Doe"}
            message_data (dict): A dictionary with keys 'thread_id', 'message_id', 
                                'sender', 'body', 'subject', and 'timestamp'.
                Example: {
                    "thread_id": "18a9f84f0c5d7bae",
                    "message_id": "CAHkZjsD0eXAmpf",
                    "sender": "user",  # Changed from 'from' to 'sender'
                    "body": "This is the email text content.",
                    "subject": "Re: Hello",
                    "timestamp": "2024-01-15T10:32:00Z"
                }
        
        Returns:
            tuple: (success: bool, error_message: str | None)
        """
        try:
            # 1. Prepare and upsert the user record
            # We use the current UTC time for the updated_at field
            current_utc_time = datetime.now(timezone.utc)
           
            # Upsert the user. on_conflict='email' tells Supabase what the unique key is.

            try:
                async with self.async_session() as session:
                    async with session.begin():
                        result = await session.execute(
                            select(EmailUsers).where(EmailUsers.email == user_data["email"])
                        )
                        existing_user = result.scalar_one_or_none()

                        if not existing_user:
                            # Insert user
                            new_user = EmailUsers(
                                email= user_data["email"],
                                name= user_data["name"],
                                updated_at = current_utc_time
                            )
                            session.add(new_user)
                            await session.flush()  # Get thread_id                        
                            await session.commit()
            except Exception as e:
                logger.error(f"Error processing thread with {user_data["email"]}: {e}")



            # 2. Insert the message record
            
            try:
                async with self.async_session() as session:
                    async with session.begin():
                        # Insert thread
                        new_thread = Emails(
                            thread_id= message_data["thread_id"],
                            email_id= message_data["message_id"],
                            user_email= user_data["email"], # This links the message to the user
                            sender= message_data["sender"], # Changed from 'from' to 'sender'
                            body= message_data["body"],
                            subject= message_data["subject"],
                            timestamp= message_data["timestamp"]
                        )
                        session.add(new_thread)
                        await session.flush()  # Get thread_id                        
                        await session.commit()
            except Exception as e:
                logger.error(f"Error processing thread with {user_data["email"]}: {e}")

            return True, None

        except KeyError as e:
            # This catches missing keys in the input dictionaries
            error_msg = f"Missing required data field: {e}"
            print(error_msg)
            return False, error_msg
        except Exception as e:
            # This catches any other unexpected errors
            error_msg = f"An unexpected error occurred: {e}"
            print(error_msg)
            return False, error_msg

if __name__=="__main__":
    client=DatabaseManager()
    user_data={"email":"test@gmail.com", "name":"Test Name"}
    message_data={
                    "thread_id": "18a9f84f0c5d7bae",
                    "message_id": "CAHkZjsD0eXBmpf",
                    "sender": "user", 
                    "body": "This is the new email text content.",
                    "subject": "Re: Hello",
                    "timestamp":  datetime.now(timezone.utc)
                }
    asyncio.run(client.store_message(user_data=user_data, message_data=message_data))
        
