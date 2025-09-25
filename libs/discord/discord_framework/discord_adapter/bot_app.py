from __future__ import annotations

from typing import Callable, Protocol, Any

import discord

from ..models import ChatContext
from .config import DiscordConfig
from .context_collector import ContextCollector
from .session_manager import SessionManager


class EngineRunner(Protocol):
    """Minimal interface the Discord adapter expects from an engine integration."""

    def register_handlers(self, session_id: str) -> None:  # pragma: no cover - interface
        ...

    async def run_engine(self, context: ChatContext, session_id: str) -> Any:  # pragma: no cover - interface
        ...

class DiscordBotApp:
    """
    Discord adapter that:
    - starts a client,
    - listens for mentions/DMs,
    - collects context,
    - registers runtime handlers with the provided engine integration,
    - executes the engine once via your global MessageBus(),
    - and replies once with the final result.

    The application must supply an `engine_factory` that knows how to register
    handlers and execute the engine for each Discord session.
    """

    def __init__(
        self,
        config: DiscordConfig,
        engine_factory: Callable[[SessionManager], EngineRunner],
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        self._bot = discord.Client(intents=intents)
        self._config = config
        self._collector = ContextCollector(last_n_messages=config.last_n_messages)
        self._sessions = SessionManager(self._bot)

        # Bridge to the engine provided by the application
        self._engine = engine_factory(self._sessions)

        # Events
        self._bot.event(self.on_ready)
        self._bot.event(self.on_message)

    async def on_ready(self) -> None:
        assert self._bot.user is not None
        print(f"Logged in as {self._bot.user} (id: {self._bot.user.id})")

    async def on_message(self, message: discord.Message) -> None:
        if self._bot.user and message.author.id == self._bot.user.id:
            return

        # Respond to mentions or DMs
        mentioned = self._bot.user in message.mentions if self._bot.user else False
        is_dm = isinstance(message.channel, discord.DMChannel)
        if is_dm:
            print(f"DM from {message.author.name}: {message.content}")
        else:
            ch_name = getattr(message.channel, "name", "DM") or "DM"
            print(f"Message from {message.author.name} in {ch_name}: {message.content}")
        if not (mentioned or is_dm):
            return

        # Session lifecycle
        sid = await self._sessions.create(message)

        # Register UI handlers for this session
        self._engine.register_handlers(sid)

        # Collect normalized context
        ctx: ChatContext = await self._collector.collect(message)
        # print(f"Collected context: {ctx}")

        # Run engine and send exactly one final reply
        result = await self._engine.run_engine(ctx, sid)

        # Duck-typed result: expect `success`, `result`, `error`
        ok = bool(getattr(result, "success", True))
        payload = getattr(result, "result", None)
        err = getattr(result, "error", None)

        if ok and payload is not None:
            await message.reply(str(payload)[: self._config.max_response_length])
        elif ok:
            await message.reply("✅ Done.")
        else:
            await message.reply(f"❌ Error: {err or 'Unknown error'}")

        await self._sessions.complete(sid, "Session completed")

    async def start(self) -> None:
        await self._bot.start(self._config.bot_token)
