from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from discord_framework.discord_adapter.context import build_chat_context_from_message
from discord_framework.discord_adapter.session_manager import SessionManager, SessionStatus
from discord_framework.models import ChatContext
from discord_framework.protocol import PromptRequestCommand, StatusEvent
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID

from .tool_chat_engine import (
    DarcyToolChatEngine,
    DarcyToolChatEngineCommand,
    DarcyToolChatEngineStatusEvent,
)


def _get_bus() -> MessageBus:
    """Fetch the global MessageBus() singleton from the environment."""
    return MessageBus()


class DarcyEngineBridge:
    """Glue code that connects the Discord adapter to the Darcy tool chat engine."""

    def __init__(
        self,
        sessions: SessionManager,
        *,
        engine_factory: Callable[[str], DarcyToolChatEngine] | None = None,
        build_command: Callable[[ChatContext, str], Any] | None = None,
        prompt_request_cls: type = PromptRequestCommand,
        status_event_cls: type = StatusEvent,
    ) -> None:
        self._sessions = sessions
        self._engine_factory = engine_factory or (lambda sid: DarcyToolChatEngine(session_id=sid))
        self._build_command = build_command or self._default_build_command
        self._prompt_cls = prompt_request_cls
        self._status_evt_cls = status_event_cls
        self._engines: Dict[str, DarcyToolChatEngine] = {}

    def _default_build_command(self, ctx: ChatContext, sid: str) -> Any:
        ctx_str = build_chat_context_from_message(ctx)
        return DarcyToolChatEngineCommand(session_id=SessionID(sid), prompt=ctx_str)

    def register_handlers(self, session_id: str) -> None:
        bus = _get_bus()
        sid_key = SessionID(session_id)

        engine = self._engine_factory(session_id)
        self._engines[session_id] = engine

        if hasattr(bus, "register_command_handler"):
            bus.register_command_handler(
                DarcyToolChatEngineCommand,
                engine.handle_command,
                session_id=sid_key,
            )  # type: ignore[attr-defined]

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(bus.start())
        except RuntimeError:
            # No running loop (e.g. during tests), skip starting the bus.
            pass

        if hasattr(bus, "register_command_handler"):
            async def _prompt_handler(cmd: Any) -> Any:
                if getattr(cmd, "session_id", None) not in (session_id, sid_key):
                    return type("R", (), {"success": False, "result": None, "error": "wrong session"})()
                prompt = getattr(cmd, "prompt", "")
                kind = getattr(cmd, "kind", "yes_no")
                timeout = getattr(cmd, "timeout_sec", 60)
                value = await self._sessions.request_input(session_id, prompt, kind, timeout)
                return type("R", (), {"success": True, "result": value, "error": None})()

            try:
                bus.register_command_handler(self._prompt_cls, _prompt_handler, session_id=sid_key)  # type: ignore[attr-defined]
            except Exception:
                bus.register_command_handler(self._prompt_cls, _prompt_handler)  # type: ignore[attr-defined]

        if hasattr(bus, "register_event_handler"):
            async def _status_handler(evt: Any) -> None:
                if getattr(evt, "session_id", None) not in (session_id, sid_key):
                    return
                status_text = getattr(evt, "status", "")
                await self._sessions.update_status(
                    session_id,
                    SessionStatus.PROCESSING,
                    status_text or None,
                )

            try:
                bus.register_event_handler(self._status_evt_cls, _status_handler, session_id=sid_key)  # type: ignore[attr-defined]
            except Exception:
                bus.register_event_handler(self._status_evt_cls, _status_handler)  # type: ignore[attr-defined]

            try:
                bus.register_event_handler(
                    DarcyToolChatEngineStatusEvent,
                    _status_handler,
                    session_id=sid_key,
                )  # type: ignore[attr-defined]
            except Exception:
                try:
                    bus.register_event_handler(DarcyToolChatEngineStatusEvent, _status_handler)  # type: ignore[attr-defined]
                except Exception:
                    pass

    async def run_engine(self, context: ChatContext, session_id: str) -> Any:
        bus = _get_bus()
        cmd = self._build_command(context, session_id)
        session_ctx = getattr(bus, "session", None)
        if callable(session_ctx):
            async with session_ctx(session_id):  # type: ignore[misc]
                print(f"Executing command: {cmd}")
                return await bus.execute(cmd)  # type: ignore[arg-type]

        return await bus.execute(cmd)
