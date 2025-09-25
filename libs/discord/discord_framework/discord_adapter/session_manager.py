from __future__ import annotations

import asyncio
import random
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import discord

from .components import YesNoView, TextPromptView


class SessionStatus(Enum):
    STARTING = "starting"
    PROCESSING = "processing"
    REQUESTING_INPUT = "requesting_input"
    INPUT_RECEIVED = "input_received"
    COMPLETED = "completed"
    ERROR = "error"


STATUS_EMOJI = {
    SessionStatus.STARTING: "🔄",
    SessionStatus.PROCESSING: "🔄",
    SessionStatus.REQUESTING_INPUT: "❓",
    SessionStatus.INPUT_RECEIVED: "✅",
    SessionStatus.COMPLETED: "✅",
    SessionStatus.ERROR: "❌",
}


@dataclass(slots=True)
class Session:
    id: str
    author: discord.abc.User
    channel: discord.abc.MessageableChannel
    status_msg: discord.Message
    status: SessionStatus = SessionStatus.STARTING
    data: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    def __init__(self, bot: discord.Client, id_len: int = 5) -> None:
        self.bot = bot
        self.id_len = id_len
        self.active: Dict[str, Session] = {}

    def _gen_id(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            sid = "".join(random.choice(chars) for _ in range(self.id_len))
            if sid not in self.active:
                return sid

    async def create(self, origin: discord.Message) -> str:
        sid = self._gen_id()
        msg = await origin.reply(f"🔄 **Session {sid} starting...**")
        self.active[sid] = Session(id=sid, author=origin.author, channel=origin.channel, status_msg=msg)
        return sid

    async def update_status(self, sid: str, status: SessionStatus, text: str | None = None) -> None:
        session = self.active.get(sid)
        if not session:
            return
        session.status = status
        if text:
            emoji = STATUS_EMOJI.get(status, "🔄")
            await session.status_msg.edit(content=f"{emoji} **Session {sid}**: {text}")

    async def complete(self, sid: str, final_text: str | None = None) -> None:
        session = self.active.get(sid)
        if not session:
            return
        await self.update_status(sid, SessionStatus.COMPLETED, final_text or "Session completed")
        try:
            await session.status_msg.delete()
        except Exception:
            pass
        del self.active[sid]

    # --- Input Requests ---

    async def request_input(self, sid: str, prompt_text: str, kind: str = "yes_no", timeout: int = 60) -> object:
        session = self.active.get(sid)
        if not session:
            return False

        await self.update_status(sid, SessionStatus.REQUESTING_INPUT, "User input requested...")

        if kind == "yes_no":
            view = YesNoView(timeout=timeout, original_author=session.author)
            prompt_msg = await session.channel.send(content=f"⚠️ **Session {sid}**: {session.author.mention}, {prompt_text}", view=view)
            await view.wait()
            await prompt_msg.edit(view=None)
            value = bool(view.value)
            await self.update_status(sid, SessionStatus.INPUT_RECEIVED, "Input received" if view.value is not None else "Timed out")
            return value

        if kind == "text":
            view = TextPromptView(timeout=timeout, original_author=session.author, prompt=prompt_text)
            prompt_msg = await session.channel.send(
                content=f"✍️ **Session {sid}**: {session.author.mention}, {prompt_text}",
                view=view,
            )
            try:
                await asyncio.wait_for(view.wait(), timeout=timeout + 2)
            except asyncio.TimeoutError:
                view.value = None
            await prompt_msg.edit(view=None)
            await self.update_status(sid, SessionStatus.INPUT_RECEIVED, "Input received" if view.value else "Timed out")
            return view.value or ""

        return False