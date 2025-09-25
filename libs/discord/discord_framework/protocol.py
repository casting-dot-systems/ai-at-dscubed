from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from llmgine.messages import Command, Event
from .models import ChatContext


@dataclass(slots=True)
class ProcessMessageCommand(Command):
    """Engine entrypoint: the adapter sends this to your engine via MessageBus().execute()."""
    context: ChatContext | None = None

@dataclass(slots=True)
class StatusEvent(Event):
    """Engine → adapter: publish progress/status for UI."""
    status: str = ""

@dataclass(slots=True)
class PromptRequestCommand(Command):
    """Engine → adapter: request confirmation or extra input from the user."""
    prompt: str = ""
    kind: Literal["yes_no", "text"] = "yes_no"
    timeout_sec: int = 60