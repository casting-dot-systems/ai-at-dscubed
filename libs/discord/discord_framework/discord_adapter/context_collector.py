from __future__ import annotations

from typing import Optional

import discord

from .context import build_chat_context
from ..models import ChatContext


class ContextCollector:
    """Collects Discord context for the current channel & message."""

    def __init__(self, last_n_messages: int = 10) -> None:
        self._n = last_n_messages

    async def collect(self, message: discord.Message) -> ChatContext:
        recent: list[discord.Message] = []
        async for m in message.channel.history(limit=self._n):
            recent.append(m)
        recent.reverse()

        replied: Optional[discord.Message] = None
        if message.reference and message.reference.message_id:
            try:
                replied = await message.channel.fetch_message(message.reference.message_id)
            except Exception:
                replied = None

        return build_chat_context(message=message, recent=recent, replied=replied)