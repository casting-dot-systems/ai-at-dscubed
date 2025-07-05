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
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from typing import NewType

import discord
from discord.ext import commands
from llmgine.llm import SessionID

from program_types import DiscordChannelID
from scrum_engine import ScrumMasterEngine
from components import YesNoView

DiscordChannelID = NewType("DiscordChannelID", str)


class SessionManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_checkups: dict[
            DiscordChannelID, tuple[SessionID, ScrumMasterEngine]
        ] = {}

    def create_sesion(
        self, channel_id: DiscordChannelID, engine: ScrumMasterEngine
    ) -> SessionID:
        session_id = SessionID(str(uuid.uuid4()))

        return session_id


class SessionStatus(Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
