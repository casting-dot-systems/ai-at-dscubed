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

from api.client import WebSocketAPIClient
from .config import DiscordBotConfig
from .engine_manager import EngineManager
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
        self.engine_manager: EngineManager = EngineManager(
            self.config, self.session_manager
        )

        self.api_client: WebSocketAPIClient = WebSocketAPIClient()

        # Set up event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)

        # Add slash command
        self.setup_slash_commands()

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

    def setup_slash_commands(self) -> None:
        """Set up slash commands for the bot."""

        @self.bot.tree.command(
            name="connect", description="Create a new session and form stable connection"
        )
        async def connect(interaction: discord.Interaction): # type: ignore
            """Slash command to create a new session and form stable connection."""
            try:
                response = await self.api_client.create_session()
                assert self.api_client.session_id is not None

                await interaction.response.send_message(
                    f"✅ Session created! Session ID: {response.session_id}", ephemeral=True
                )

                # Get engine types
                response = await self.api_client.use_websocket("get_engine_types", {})
                if not response or response.type != "get_engine_types_res":
                    await interaction.followup.send("Failed to get engine types", ephemeral=True)
                    return

                engine_types = response.data.get("engine_types", [])

                # Choose engine
                view = EngineSelectorView(items=engine_types)
                await interaction.followup.send(
                    "Please select an engine to use:",
                    view=view,
                    ephemeral=True
                )

                # Collect response from the view
                selected_engine = await view.wait_for_selection()
                if selected_engine:
                    await interaction.followup.send(
                        f"Connecting to: **{selected_engine}**", ephemeral=True
                    )
                    # Create the engine
                    response = await self.api_client.use_websocket("link_engine", {"engine_type": selected_engine})
                    if response and response.type == "link_engine_res":
                        engine_id = response.data.get("engine_id")
                        await interaction.followup.send(
                            f"Engine connected: **{selected_engine}**, engine ID: {engine_id}", ephemeral=True
                        )
                    else:
                        await interaction.followup.send("Failed to connect to engine", ephemeral=True)
                else:
                    await interaction.followup.send("No engine selected", ephemeral=True)

            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to create session: {str(e)}", ephemeral=True
                )




async def main() -> None:
    """Main entry point for the bot."""
    bot: DarcyBot = DarcyBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
