from __future__ import annotations

from typing import Optional

import discord

from ..models import (
    AttachmentInfo,
    AuthorInfo,
    ChannelInfo,
    ChatContext,
    GuildInfo,
    MessageInfo,
)


def to_author_info(user: discord.abc.User) -> AuthorInfo:
    dn = getattr(user, "display_name", None) or getattr(user, "global_name", None) or user.name
    return AuthorInfo(id=str(user.id), display_name=str(dn))


def to_channel_info(channel: discord.abc.GuildChannel | discord.DMChannel | discord.Thread) -> ChannelInfo:
    if isinstance(channel, discord.Thread):
        return ChannelInfo(id=str(channel.id), name=channel.name, type="thread")
    if isinstance(channel, discord.DMChannel):
        return ChannelInfo(id=str(channel.id), name="DM", type="dm")
    name = getattr(channel, "name", "unknown")
    return ChannelInfo(id=str(getattr(channel, "id", "unknown")), name=str(name), type="text")


def to_guild_info(guild: Optional[discord.Guild]) -> GuildInfo:
    if guild is None:
        return GuildInfo(id=None, name=None)
    return GuildInfo(id=str(guild.id), name=guild.name)


def to_message_info(msg: discord.Message) -> MessageInfo:
    return MessageInfo(author=to_author_info(msg.author), content=msg.content, id=str(msg.id))


def to_attachment_info(att: discord.Attachment) -> AttachmentInfo:
    return AttachmentInfo(filename=att.filename, url=att.url)


def build_chat_context(
    *,
    message: discord.Message,
    recent: list[discord.Message],
    replied: Optional[discord.Message],
) -> ChatContext:
    mentions = [to_author_info(u) for u in message.mentions]
    attachments = [to_attachment_info(a) for a in message.attachments]
    recent_infos = [to_message_info(m) for m in recent]
    reply_info = to_message_info(replied) if replied else None

    return ChatContext(
        content=message.content,
        author=to_author_info(message.author),
        channel=to_channel_info(message.channel),
        guild=to_guild_info(message.guild),
        mentions=mentions,
        attachments=attachments,
        reply_to=reply_info,
        recent_messages=recent_infos,
    )

def build_chat_context_from_message(context: ChatContext) -> str:
    result = ""
    result += f"Message to Respond To: {context.content}\n"
    result += f"Author: {context.author.display_name}\n"
    result += f"Channel: {context.channel.name}\n"
    result += f"Reply to: {context.reply_to}\n"
    result += f"Recent messages: {context.recent_messages}\n"
    return result