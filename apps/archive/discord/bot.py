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

# Configure logging
logging.basicConfig(level=logging.INFO)


class DarcyBot:
    def __init__(self) -> None:
        # Load configuration
        self.config = DiscordBotConfig.load_from_env()

        # Initialize Discord bot
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        self.bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

        # Initialize managers
        self.session_manager: SessionManager = SessionManager(self.bot)
        self.message_processor: MessageProcessor = MessageProcessor(
            self.config, self.session_manager
        )
        self.engine_manager: EngineManager = EngineManager(
            self.config, self.session_manager
        )

        # Set up event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

    async def on_ready(self) -> None:
        """Called when the bot is ready to start."""
        print(f"Logged in as {self.bot.user}")

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        if message.author == self.bot.user:
            return

        if message.mention_everyone:
            return

        assert self.bot.user is not None
        if self.bot.user.mentioned_in(message):
            # Process the message
            (
                processed_message,
                session_id,
            ) = await self.message_processor.process_mention(message)

            # Create command and use engine
            from darcy.notion_crud_engine_v3 import NotionCRUDEnginePromptCommand

            command = NotionCRUDEnginePromptCommand(prompt=processed_message.content)
            result = await self.engine_manager.use_engine(command, session_id)

            # Send response
            if result.result:
                await message.reply(
                    f"{result.result[: self.config.max_response_length]}"
                )
            else:
                await message.reply(
                    "❌ An error occurred. Sorry about that, please forgive me!!"
                )

            # Complete the session
            await self.session_manager.complete_session(session_id, "Session completed")

        await self.bot.process_commands(message)

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


async def main() -> None:
    """Main entry point for the bot."""
    bot: DarcyBot = DarcyBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
