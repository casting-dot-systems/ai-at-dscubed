"""
This file contains the session manager for the discord bot, including:
- Session status types
- Session manager class
- Session expiration
- Session data updates
- Session input request
- Session completion
"""

import asyncio
import random
import string
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands
from llmgine.llm import SessionID, EngineID

from .components import YesNoView
from .api.client import WebSocketAPIClient


# Session status types
class SessionStatus(Enum):
    STARTING = "starting"
    INITIATING_SESSION = "initiating_session"
    INITIATING_ENGINE = "initiating_engine"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    REQUESTING_INPUT = "requesting_input"
    INPUT_RECEIVED = "input_received"
    CONTINUING = "continuing"
    COMPLETED = "completed"
    ERROR = "error"
    IDLE = "idle"


STATUS_EMOJI = {
    SessionStatus.STARTING: "🔄",
    SessionStatus.INITIATING_SESSION: "🎲",
    SessionStatus.INITIATING_ENGINE: "🕹️",
    SessionStatus.PROCESSING: "🔄",
    SessionStatus.WAITING_FOR_INPUT: "⏳",
    SessionStatus.REQUESTING_INPUT: "❓",
    SessionStatus.INPUT_RECEIVED: "✓",
    SessionStatus.CONTINUING: "🔄",
    SessionStatus.COMPLETED: "✅",
    SessionStatus.ERROR: "❌",
    SessionStatus.IDLE: "💤",
}

class SessionData:
    session_id: SessionID
    message: discord.Message
    session_status_msg: discord.Message
    session_msgs: List[discord.Message]
    author: discord.Member | discord.User
    channel: discord.TextChannel | discord.DMChannel
    status: SessionStatus
    result: Optional[Any]
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    engine_id: Optional[EngineID]
    expires_at: Optional[datetime]

    def __init__(self, session_id: SessionID, 
                 message: discord.Message, 
                 session_status_msg: discord.Message, 
                 session_msgs: List[discord.Message], 
                 author: discord.Member | discord.User, 
                 channel: discord.TextChannel | discord.DMChannel, 
                 data: Optional[Dict[str, Any]] = None,
                 engine_id: Optional[EngineID] = None,
                 expires_at: Optional[datetime] = None):
        self.session_id = session_id
        self.message = message
        self.session_status_msg = session_status_msg
        self.session_msgs = session_msgs
        self.author = author
        self.channel = channel
        self.status = SessionStatus.STARTING
        self.result = None
        self.data = {}
        self.created_at = discord.utils.utcnow()
        self.updated_at = discord.utils.utcnow()
        self.engine_id = engine_id

class SessionManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions: Dict[str, SessionData] = {}
        self.id_length: int = 5
        self.api_client: Optional[WebSocketAPIClient] = None

    def generate_session_id(self) -> str:
        """Generate a random alphanumeric session ID"""
        chars = string.ascii_uppercase + string.digits
        session_id = "".join(random.choice(chars) for _ in range(self.id_length))

        # Ensure uniqueness
        while session_id in self.active_sessions:
            session_id = "".join(random.choice(chars) for _ in range(self.id_length))

        return session_id
    
    async def create_session(self, user_id: str) -> SessionID:
        if self.api_client is None:
            raise Exception("API client not initialized")
        
        await self.update_session_status(
                user_id,
                SessionStatus.INITIATING_SESSION,
                f"Creating session...",
            )
        response = await self.api_client.use_websocket("create_session", {})
        if response and response.data.get("session_id") is not None:
            session_id = SessionID(str(response.data.get("session_id")))
            return session_id
        else:
            raise Exception("Failed to create session")


    async def use_session(
        self,
        message: discord.Message,
        initial_data: Optional[Dict[str, Any]] = None,
        expire_after_minutes: Optional[int] = None,
    ) -> SessionID:
        """Create a new session and return its ID"""
        # Check if the sender is already in a session
        user_id = str(message.author.id)
        
        # Create initial session message
        session_msg = await message.reply(f"🔄 **Thinking...**")
        
        
        if user_id in self.active_sessions:
            session_id : SessionID = self.active_sessions[user_id].session_id
        else:
            session_id = await self.create_session(user_id)
        
            # Initialize session data
            self.active_sessions[user_id] = SessionData(
                session_id=session_id,
                message=message,
                session_status_msg=session_msg,
                session_msgs=[],
                data=initial_data or {},
                author=message.author,
                channel=message.channel,
            )

            # Schedule expiration if requested
            if expire_after_minutes:
                self.active_sessions[user_id].expires_at = (
                    discord.utils.utcnow() + timedelta(minutes=expire_after_minutes)
                )

                # Schedule the expiration task
                self.bot.loop.create_task(
                    self._expire_session(user_id, expire_after_minutes)
                )

        return session_id

    # Add this method to handle session expiration
    async def _expire_session(self, user_id: str, minutes: int):
        """Background task to expire a session after a set time"""
        await asyncio.sleep(minutes * 60)  # Convert to seconds

        # Check if session still exists and hasn't been completed yet
        if (
            user_id in self.active_sessions
            and self.active_sessions[user_id].status != SessionStatus.COMPLETED
        ):
            await self.update_session_status(
                user_id,
                SessionStatus.COMPLETED,
                f"Session expired after {minutes} minutes",
            )

    def get_session(self, user_id: str) -> Optional[SessionData]:
        """Get session data by ID"""
        return self.active_sessions.get(user_id)

    def get_sessions_by_status(self, status: SessionStatus) -> List[SessionData]:
        """Get all sessions with a specific status"""
        return [
            session
            for session in self.active_sessions.values()
            if session.status == status
        ]

    async def update_session_status(
        self, user_id: str, status: SessionStatus, message: Optional[str] = None
    ) -> Optional[bool]:
        """Update a session's status and optionally its message"""
        if user_id not in self.active_sessions:
            return False

        session = self.active_sessions[user_id]
        session.status = status
        session.updated_at = discord.utils.utcnow()

        # TODO temp solution
        if message == "finished":
            return None

        if message:
            emoji = STATUS_EMOJI.get(status, "🔄")
            await session.session_status_msg.edit(
                content=f"{emoji} **{message}**"
            )

        if status == SessionStatus.COMPLETED:
            await session.session_status_msg.delete()

        return True

    async def update_session_data(
        self, user_id: str, data_updates: Dict[str, Any]
    ) -> bool:
        """Update a session's data dictionary"""
        if user_id not in self.active_sessions:
            return False

        self.active_sessions[user_id].data.update(data_updates)
        self.active_sessions[user_id].updated_at = discord.utils.utcnow()
        return True

    async def request_user_input(
        self,
        user_id: str,
        prompt_text: str,
        timeout: int = 60,
        input_type: str = "yes_no",
    ) -> bool:
        """Request input from a user for a specific session"""
        if user_id not in self.active_sessions:
            raise ValueError("Session not found")

        session = self.active_sessions[user_id]

        # Update status
        await self.update_session_status(
            user_id, SessionStatus.REQUESTING_INPUT, "User input requested..."
        )

        result: Optional[bool] = None

        if input_type == "yes_no":
            # Create the view for Yes/No input
            view = YesNoView(timeout=timeout, original_author=session.author)
            prompt_msg = await session.channel.send(
                content=f"⚠️ **{session.author.mention}, {prompt_text}",
                view=view,
            )
            session.session_msgs.append(prompt_msg)
            # Wait for the user to respond
            await view.wait()

            # Process the result
            if view.value is None:
                result = False
                await prompt_msg.edit(content="⏱️ Request timed out", view=None)
            else:
                result = view.value
                resp_text = (
                    f"✅ **Accepted**: {prompt_text}"
                    if view.value
                    else f"❌ **Declined**: {prompt_text}"
                )
                await prompt_msg.edit(content=f"{resp_text}", view=None)

        # Update session and return result
        await self.update_session_status(user_id, SessionStatus.INPUT_RECEIVED)
        await self.update_session_data(user_id, {"last_input": result})

        assert result is not None
        return result

    async def complete_session(
        self, user_id: str, final_message: Optional[str] = None
    ) -> bool:
        """Mark a session as completed"""
        if not await self.update_session_status(
            user_id, SessionStatus.COMPLETED, final_message or "Session completed"
        ):
            return False

        for msg in self.active_sessions[user_id].session_msgs:
            await msg.delete()

        # You can choose to keep completed sessions in memory for reference
        # or remove them to free up memory
        # del self.active_sessions[session_id]

        return True
