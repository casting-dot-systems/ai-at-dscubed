"""
This module creates and assembles the discord bot.
Components include:
- Configuration
- Session manager
- Message processor
- Engine manager

The bot is started here.
"""

import logging
import threading
from datetime import datetime

import discord
from discord.ext import commands
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.bus.bus import MessageBus
from llmgine.messages import CommandResult
from custom_types.discord import DiscordChannelID

from scrum_checkup_types import CheckUpEvent, CheckUpEventContext, CheckUpFinishedEvent
from scrum_checkup_engine import request_end_conversation
from config import DiscordBotConfig
from scrum_checkup_engine import (
    ScrumMasterEngine,
    ScrumMasterCommand,
    ScrumMasterConfirmEndConversationCommand,
)
from components import YesNoView


# Configure logging
logging.basicConfig(level=logging.INFO)


class ScrumMasterBot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        # Load configuration
        self.config = DiscordBotConfig.load_from_env()

        # Initialize Discord bot
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        self.bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

        # Initialize managers
        self.channel_register: dict[
            DiscordChannelID, tuple[ScrumMasterEngine, CheckUpEventContext]
        ] = {}

        # Set up event handlers
        self.bot.event(self.on_message)
        self.bot.event(self.on_ready)

        # Add slash command
        self.setup_slash_commands()

        # Mark as initialized
        self._initialized = True

    def setup_slash_commands(self) -> None:
        """Set up slash commands for the bot."""

        @self.bot.tree.command(
            name="scrum-checkup", description="Start a scrum checkup for a user"
        )
        async def scrum_checkup(interaction: discord.Interaction, user: discord.Member): # type: ignore
            """Slash command to trigger a scrum checkup for a specified user."""
            try:
                # Publish the CheckUpEvent
                await MessageBus().publish(
                    CheckUpEvent(
                        user_discord_id=str(user.id),
                        scheduled_time=datetime.now(),
                    )
                )

                await interaction.response.send_message(
                    f"✅ Scrum checkup initiated for {user.mention}!", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to initiate scrum checkup: {str(e)}", ephemeral=True
                )

    @classmethod
    def get_instance(cls) -> "ScrumMasterBot":
        """Get the singleton instance. Preferred method for accessing the singleton."""
        if cls._instance is None:
            cls()
        return cls._instance  # type: ignore

    async def create_session(
        self,
        checkup_context: CheckUpEventContext,
    ) -> None:
        engine = ScrumMasterEngine(
            checkup_context.system_prompt,
            checkup_context.session_id,
            checkup_context.checkup_channel_id,
        )
        self.channel_register[checkup_context.checkup_channel_id] = (
            engine,
            checkup_context,
        )
        await engine.tool_manager.register_tool(request_end_conversation)
        MessageBus().register_command_handler(
            ScrumMasterConfirmEndConversationCommand,
            self.handle_end_conversation, # type: ignore
            session_id=checkup_context.session_id,
        )
        init_message = await engine.handle_command(
            ScrumMasterCommand(
                prompt="Start the process", session_id=checkup_context.session_id
            )
        )
        channel = self.bot.get_channel(int(checkup_context.checkup_channel_id))
        if channel is None:
            raise ValueError(
                f"Channel {int(checkup_context.checkup_channel_id)} not found"
            )
        await channel.send( # type: ignore
            f"# Scrum Checkup <@{checkup_context.discord_id}>\n\n"
            + (init_message.result if init_message.result else "")
        )

    async def end_session(self, channel_id: DiscordChannelID) -> None:
        print(f"Ending session for channel {channel_id}")
        conversation = await self.channel_register[channel_id][0].extract_conversation()
        self.channel_register[channel_id][1].conversation = conversation # type: ignore
        await MessageBus().publish(
            CheckUpFinishedEvent(checkup_context=self.channel_register[channel_id][1])
        )
        self.channel_register.pop(channel_id)

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected to Discord."""
        print(f"Bot is ready! Logged in as {self.bot.user}")
        # Now the bot can access channels

        # Sync slash commands
        try:
            synced = await self.bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        # print(f"\n\nScrumMasterBot instance on_ready: {self.get_instance()}\n\n")
        # await MessageBus().publish(
        #     CheckUpEvent(
        #         user_discord_id="774065995508744232",
        #         scheduled_time=datetime.now() + timedelta(seconds=10),
        #     )
        # )

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        if message.author == self.bot.user:
            return

        if message.mention_everyone:
            return

        if str(message.channel.id) in self.channel_register.keys():
            async with self.show_loading_message(
                DiscordChannelID(str(message.channel.id)), message
            ):
                response = await self.channel_register[
                    DiscordChannelID(str(message.channel.id))
                ][0].handle_command(ScrumMasterCommand(prompt=message.content))
            await message.reply(response.result)
        else:
            print("Message received in unregistered channel")

    def show_loading_message(
        self, channel_id: DiscordChannelID, original_message: discord.Message
    ) -> "LoadingMessageContext":
        return LoadingMessageContext(self.bot, channel_id, original_message)

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

    async def request_end_conversation(
        self,
        channel_id: DiscordChannelID,
    ) -> bool:
        """Request input from a user for a specific session"""

        view = YesNoView(timeout=60)
        channel = self.bot.get_channel(int(channel_id))
        prompt_msg = await channel.send( # type: ignore
            content="⚠️ Stella would like to end the conversation. Do you agree?",
            view=view,
        )
        await view.wait()

        # Process the result
        if view.value is None:
            result = False
            await prompt_msg.edit(content="⏱️ Request timed out", view=None) # type: ignore
        else:
            result = view.value
            resp_text = (
                "✅ End conversation request accepted"
                if view.value
                else "❌ End conversation request declined"
            )
            await prompt_msg.edit(content=f"{resp_text}", view=None) # type: ignore

        return result

    async def handle_end_conversation(
        self, command: ScrumMasterConfirmEndConversationCommand
    ) -> CommandResult:
        result = await self.request_end_conversation(command.channel_id)
        if result:
            await self.end_session(command.channel_id)
        return CommandResult(
            success=True,
            result=result,
        )


class LoadingMessageContext:
    def __init__(
        self,
        bot: commands.Bot,
        channel_id: DiscordChannelID,
        original_message: discord.Message,
    ) -> None:
        self.bot = bot
        self.channel_id = channel_id
        self.original_message = original_message
        self.loading_message: discord.Message | None = None

    async def __aenter__(self) -> "LoadingMessageContext":
        self.loading_message = await self.original_message.reply(
            "🔄 Generating Response..."
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self.loading_message:
            try:
                await self.loading_message.delete()
            except discord.NotFound:
                # Message was already deleted
                pass
            except discord.Forbidden:
                # Bot doesn't have permission to delete
                pass
