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

from .config import DiscordBotConfig
from .message_processor import MessageProcessor
from .session_manager import SessionManager
from .engine_manager import EngineManager

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



        self.engine_connected: bool = False

    async def on_ready(self) -> None:
        """Called when the bot is ready to start."""
        print(f"Logged in as {self.bot.user}")

        # Connect to the engine backend
        api_client = await self.engine_manager.initialize_api_client()
        self.session_manager.api_client = api_client
        print("Connection with backend established")


        # # Sync slash commands
        # try:
        #     synced = await self.bot.tree.sync(guild=discord.Object(id=int(self.config.guild_id)))
        #     print(f"Synced {len(synced)} command(s)")
        # except Exception as e:
        #     print(f"Failed to sync commands: {e}")

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

            
            # Process message through engine manager
            result = await self.engine_manager.process_user_message(
                processed_message.content, session_id, str(message.author.id)
            )
            
            # Send response
            await message.reply(result)

            # # Complete the session
            # await self.session_manager.complete_session(session_id, "Session completed")

        await self.bot.process_commands(message)

    async def start(self):
        """Start the bot and all necessary services."""
        try:
            # Run the bot
            await self.bot.start(self.config.bot_key)
        finally:
            # Clean up engine manager
            await self.engine_manager.cleanup()

async def main() -> None:
    """Main entry point for the bot."""
    bot: DarcyBot = DarcyBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
