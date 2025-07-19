"""
This module processes messages from the discord server.
It processes:
- mentions
- author payload
- chat history
- reply payload
"""

import logging
from typing import Optional

import discord

from custom_tools.general.functions import get_all_facts, get_user_info
from custom_tools.brain.notion.data import (
    UserData,
    discord_user_id_type,
    get_user_from_discord_id,
)

from .config import DiscordBotConfig
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self, config: DiscordBotConfig, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager

    async def process_mention(
        self, message: discord.Message
    ) -> tuple[discord.Message, str]:
        """Process a message where the bot is mentioned."""

        # TODO need a session id type
        session_id: str = await self.session_manager.create_session(
            message, expire_after_minutes=1
        )

        # Process user mentions
        user_mentions = self._process_mentions(message)
        author_payload = self._create_author_payload(message)
        chat_history = await self._get_chat_history(message)
        reply_payload = await self._process_reply(message)

        # Combine all payloads
        message.content = (
            message.content
            + f"\n\n{reply_payload}\n\n{author_payload}\n\n{user_mentions}\n\n{chat_history}"
        )

        return message, session_id

    def _process_mentions(self, message: discord.Message) -> str:
        """Process user mentions in the message."""
        user_mentions = [user.id for user in message.mentions]
        mentions_payload: list[dict[discord_user_id_type, str]] = []
        for user_mention in user_mentions:
            if user_mention == self.config.bot_id:
                continue
            discord_id = discord_user_id_type(str(user_mention))
            user_data: UserData | None = get_user_from_discord_id(discord_id)
            if user_data:
                mentions_payload.append({discord_id: user_data.notion_id})
            else:
                mentions_payload.append({discord_id: "Unknown Notion ID"})
        return str(mentions_payload)

    def _create_author_payload(self, message: discord.Message) -> str:
        """Create payload for the message author."""
        author_discord_id = discord_user_id_type(str(message.author.id))
        author_data: UserData | None = get_user_from_discord_id(author_discord_id)
        author_notion_id = "Unknown Notion ID"
        if author_data:
            author_notion_id = author_data.notion_id
        author_info = get_user_info(author_discord_id)
        author_facts = get_all_facts(author_discord_id)
        return (
            "The Author of this message is:"
            + str({author_discord_id: author_notion_id})
            + "Some info about the author are: "
            + author_info
            + "Some facts about the author are: "
            + author_facts
        )

    async def _get_chat_history(self, message: discord.Message) -> str:
        """Get recent chat history from the channel."""
        chat_history: list[str] = []
        async for msg in message.channel.history(limit=20):
            if msg.author.id == self.config.bot_id:
                if "Result" not in msg.content:
                    continue
            chat_history.append(f"{msg.author.display_name}: {msg.content}")

        chat_history.reverse()
        return "Chat History:\n" + "\n".join(chat_history)

    async def _process_reply(self, message: discord.Message) -> str:
        """Process message replies."""
        if message.reference is None:
            return ""

        msg_id: Optional[int] = message.reference.message_id
        if msg_id is None:
            return "No message id was found"
        replied_message = await message.channel.fetch_message(msg_id)
        return f"The current request is responding to a message, and that message is: {replied_message.author.display_name}: {replied_message.content}"
