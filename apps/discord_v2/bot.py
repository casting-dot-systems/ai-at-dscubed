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

from .api.client import WebSocketAPIClient
from .config import DiscordBotConfig
from .message_processor import MessageProcessor
from .session_manager import SessionManager
from .components import EngineSelectorView

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

        self.api_client: WebSocketAPIClient = WebSocketAPIClient()

        # Set up event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)



        self.connected_to_engine: bool = False

    async def on_ready(self) -> None:
        """Called when the bot is ready to start."""
        print(f"Logged in as {self.bot.user}")

        # Sync slash commands
        try:
            synced = await self.bot.tree.sync(guild=discord.Object(id=int(self.config.guild_id)))
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

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
            print(f"Connected to engine: {self.connected_to_engine}")
            if not self.connected_to_engine:
                await self.connect(message)

            result = await self.api_client.use_websocket("use_engine", {"prompt": processed_message.content})
            print(f"Result: {result}")
            # Send response
            if result and result.type == "use_engine_res":
                if result.data.get("success"):
                    await message.reply(
                        f"{result.data.get('result')}"
                )
            elif result and result.type == "use_engine_res":
                await message.reply(
                    f"❌ An error occurred. Sorry about that, please forgive me!!\n{result.data.get('message')}"
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

    async def connect(self, message: discord.Message):
        """Slash command to create a new session and form stable connection."""
        try:
            response = await self.api_client.create_session()
            assert self.api_client.session_id is not None

            # await message.reply(
            #     f"✅ Session created! Session ID: {response.session_id}"
            # )

            # Get engine types
            response = await self.api_client.use_websocket("get_engine_types", {})
            if not response or response.type != "get_engine_types_res":
                await message.reply("Failed to get engine types")
                return

            engine_types = response.data.get("engine_types", [])

            # Choose engine
            view = EngineSelectorView(items=engine_types)
            await message.reply(
                "Please select an engine to use:",
                view=view
            )

            # Collect response from the view
            selected_engine = await view.wait_for_selection()
            if selected_engine:
                # await message.reply(
                #     f"Connecting to: **{selected_engine}**"
                # )
                # Create the engine
                response = await self.api_client.use_websocket("link_engine", {"engine_type": selected_engine})
                if response and response.type == "link_engine_res":
                    engine_id = response.data.get("engine_id")
                    self.connected_to_engine = True
                    # await message.reply(
                    #     f"Engine connected: **{selected_engine}**, engine ID: {engine_id}"
                    # )
                else:
                    await message.reply("Failed to connect to engine")
            else:
                await message.reply("No engine selected")

        except Exception as e:
            await message.reply(
                f"❌ Failed to create session: {str(e)}"
            )




async def main() -> None:
    """Main entry point for the bot."""
    bot: DarcyBot = DarcyBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
