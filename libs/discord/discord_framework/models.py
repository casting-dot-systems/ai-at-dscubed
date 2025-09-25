from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class AuthorInfo:
    id: str
    display_name: str


@dataclass(slots=True)
class AttachmentInfo:
    filename: str
    url: str


@dataclass(slots=True)
class MessageInfo:
    author: AuthorInfo
    content: str
    id: Optional[str] = None


@dataclass(slots=True)
class ChannelInfo:
    id: str
    name: str
    type: str  # text/thread/dm/etc


@dataclass(slots=True)
class GuildInfo:
    id: Optional[str]
    name: Optional[str]


@dataclass(slots=True)
class ChatContext:
    """Transport-agnostic context a chatbot can use."""
    content: str
    author: AuthorInfo
    channel: ChannelInfo
    guild: GuildInfo
    mentions: list[AuthorInfo] = field(default_factory=list)
    attachments: list[AttachmentInfo] = field(default_factory=list)
    reply_to: Optional[MessageInfo] = None
    recent_messages: list[MessageInfo] = field(default_factory=list)  # chronological