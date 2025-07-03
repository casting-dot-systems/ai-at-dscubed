"""
This module creates and assembles the discord bot.
Components include:
- Configuration
- Session manager
- Message processor
- Engine manager

The bot is started here.
"""

import asyncio
import logging

import discord
from discord.ext import commands
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.bus.bus import MessageBus

from config import DiscordBotConfig
from engine_manager import EngineManager
from message_processor import MessageProcessor
from session_manager import SessionManager
from scrum_engine import (
    ScrumMasterEngine,
    ScrumMasterCommand,
    ScrumMasterEngineStatusEvent,
    ScrumMasterConfirmEndConversationCommand,
    ScrumMasterEngineToolResultEvent,
)

# Configure logging
logging.basicConfig(level=logging.INFO)


class ScrumMasterBot:
    def __init__(self) -> None:
        # Load configuration
        self.config = DiscordBotConfig.load_from_env()

        # Initialize Discord bot
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        self.bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

        # Initialize managers
        self.channel_register: dict[str, tuple[str, ScrumMasterEngine]] = {}

        # Set up event handlers
        self.bot.event(self.on_message)

    def create_session(
        self, session_id: str, channel_id: str, engine: ScrumMasterEngine
    ) -> None:
        self.channel_register[channel_id] = (session_id, engine)

    def end_session(self, session_id: str) -> None:
        self.channel_register.pop(session_id)

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        if message.author == self.bot.user:
            return

        if message.mention_everyone:
            return

        assert self.bot.user is not None

        if str(message.channel.id) in self.channel_register.keys():
            response = await self.channel_register[str(message.channel.id)][
                1
            ].handle_command(ScrumMasterCommand(prompt=message.content))
            await message.reply(response.result)
        else:
            print("Message received in unregistered channel")

    async def start(self):
        """Start the bot and all necessary services."""
        # Bootstrap the application
        bootstrap = ApplicationBootstrap(self.config)
        await bootstrap.bootstrap()

        # Start the message bus
        bus: MessageBus = MessageBus()
        await bus.start()

        try:
            # Run the bot
            await self.bot.start(self.config.bot_key)
        finally:
            # Ensure the bus is stopped when the application ends
            await bus.stop()


main_darcy_bot: ScrumMasterBot = ScrumMasterBot()


async def main() -> None:
    """Main entry point for the bot."""
    main_darcy_bot.create_session(
        "123", "1389598040037396610", ScrumMasterEngine("123", "123")
    )
    await main_darcy_bot.start()


if __name__ == "__main__":
    asyncio.run(main())
