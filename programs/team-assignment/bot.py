"""
This module contains the bot for the team assignment program.

The bot is responsible for handling the bot commands and events.
"""

import asyncio
import logging
import threading
from typing import Optional, NewType, Dict, Any

import discord
from discord.ext import commands
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.bus.bus import MessageBus
from config import DiscordBotConfig
from session_manager import SessionManager
from groupfunctions import GroupFunctions

from team_engine import (
    TeamAssignmentCommand, 
    TeamAssignmentEngine, 
)

DiscordChannelID = NewType("DiscordChannelID", str)
SessionContext = NewType("SessionContext", Dict[str, Any])

logging.basicConfig(level=logging.INFO)

class TeamAssignmentBot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        if hasattr(self, "_initialized"):
            return 
        
        self.config = DiscordBotConfig.load_from_env()

        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        self.bot.event(self.on_message)
        self.bot.event(self.on_ready)
        self.engine = TeamAssignmentEngine()
        self.session_manager = SessionManager(self.bot)
        self.group_functions = GroupFunctions()

    @classmethod
    def get_instance(cls) -> "TeamAssignmentBot":
        if cls._instance is None:
            cls()
        return cls._instance
    
    async def start(self) -> None:
        bootstrap = ApplicationBootstrap(self.config)
        await bootstrap.bootstrap()

        bus: MessageBus = MessageBus()
        await bus.start()

        try:
            await self.bot.start(self.config.bot_key)
        finally:
            await bus.stop()

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return 
        
        if message.mention_everyone:
            return 

        assert self.bot.user is not None 
        if self.bot.user.mentioned_in(message):
            await self.session_manager.create_session(
                channel_id=str(message.channel.id),
                engine=self.engine,
            )

            command = TeamAssignmentCommand(prompt=message.content)
            await self.engine.handle_command(command)
    
    async def notify_group(
            self, group_name: str, message: str, channel_id: DiscordChannelID) -> None:
        group = await self.group_functions.get_group(group_name)
        if group is None:
            raise ValueError(f"Group {group_name} not found")

        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            raise ValueError(f"Channel {int(group['channel_id'])} not found")

        mention = []
        for member in group["members"]:
            user_id = member["discord_id"]
            mention.append(f"<@{user_id}>")

        mentions = " ".join(mention)
        await channel.send(
            f"{mentions} {message}"
        )

    async def on_ready(self) -> None:
        print(f"Bot is ready! Logged in as {self.bot.user}")

