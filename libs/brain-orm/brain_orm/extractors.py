"""
Data extractors for various systems, integrated with SQLAlchemy ORM.
"""

import os
import ssl
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID

import pandas as pd
from discord import Client, Intents, TextChannel
from dotenv import load_dotenv

from .api import BrainCoreAPI
from .models import Message, Component, Member


class DiscordOrmExtractor:
    """
    Discord data extractor that uses SQLAlchemy ORM for data persistence.
    Enhanced version of the original DiscordExtractor from libs/brain.
    """

    def __init__(self, api: BrainCoreAPI, org_id: str, bot_token: Optional[str] = None, guild_id: Optional[int] = None):
        """
        Initialize the Discord ORM extractor.

        Args:
            api: BrainCoreAPI instance for database operations
            org_id: Organization identifier
            bot_token: Discord bot token (from env if not provided)
            guild_id: Discord guild ID (from env if not provided)
        """
        # Disable SSL verification
        ssl._create_default_https_context = ssl._create_unverified_context

        # Load environment variables
        load_dotenv()
        self.api = api
        self.org_id = org_id
        self.token = bot_token or os.getenv("BOT_KEY")
        self.guild_id = guild_id or int(os.getenv("TEST_SERVER_ID", "0"))

        if not self.token or not self.guild_id:
            raise ValueError("BOT_KEY and TEST_SERVER_ID must be set in .env file or provided as arguments")

        # Configure intents
        self.intents = Intents.default()
        self.intents.message_content = True
        self.intents.guilds = True
        self.intents.guild_messages = True

    def create_client(self) -> Client:
        """Create and return a new Discord client with configured intents."""
        return Client(intents=self.intents)

    async def sync_discord_channels(self) -> List[Component]:
        """
        Sync Discord channels/components to the database.

        Returns:
            List of synced Component objects
        """
        client = self.create_client()
        synced_components = []

        @client.event
        async def on_ready():
            try:
                print("Syncing Discord channels...")
                guild = client.get_guild(self.guild_id)
                if not guild:
                    raise ValueError(f"Guild with ID {self.guild_id} not found")

                for channel in guild.text_channels:
                    component = await self.api.upsert_component(
                        org_id=self.org_id,
                        system="discord",
                        component_id=str(channel.id),
                        component_type="channel",
                        name=channel.name,
                        is_active=True,
                        raw_data={
                            "discord_channel_id": channel.id,
                            "created_at": channel.created_at.isoformat(),
                            "position": channel.position,
                            "category": channel.category.name if channel.category else None,
                        },
                    )
                    synced_components.append(component)

                    # Sync threads for this channel
                    threads = [t async for t in channel.archived_threads(limit=None)]
                    active_threads = channel.threads

                    for thread in [*threads, *active_threads]:
                        thread_component = await self.api.upsert_component(
                            org_id=self.org_id,
                            system="discord",
                            component_id=str(thread.id),
                            component_type="thread",
                            name=thread.name,
                            parent_component_id=str(channel.id),
                            is_active=not thread.archived if hasattr(thread, 'archived') else True,
                            raw_data={
                                "discord_thread_id": thread.id,
                                "parent_channel_id": channel.id,
                                "created_at": thread.created_at.isoformat(),
                                "archived": getattr(thread, 'archived', False),
                                "auto_archive_duration": getattr(thread, 'auto_archive_duration', None),
                            },
                        )
                        synced_components.append(thread_component)

                print(f"Synced {len(synced_components)} Discord components")

            except Exception as e:
                print(f"Error syncing Discord channels: {str(e)}")
                raise
            finally:
                await client.close()

        await client.start(self.token)
        return synced_components

    async def sync_discord_messages(self, limit_per_channel: Optional[int] = None) -> List[Message]:
        """
        Sync Discord messages to the database.

        Args:
            limit_per_channel: Maximum messages per channel/thread (None for all)

        Returns:
            List of synced Message objects
        """
        client = self.create_client()
        synced_messages = []

        @client.event
        async def on_ready():
            try:
                print("Syncing Discord messages...")
                guild = client.get_guild(self.guild_id)
                if not guild:
                    raise ValueError(f"Guild with ID {self.guild_id} not found")

                for channel in guild.text_channels:
                    print(f"Processing channel: {channel.name}")

                    # Sync channel messages
                    async for discord_message in channel.history(limit=limit_per_channel):
                        # Ensure member exists
                        author_member_id = await self.api.ensure_member_for_discord(
                            org_id=self.org_id,
                            discord_user_id=str(discord_message.author.id),
                            display_name=str(discord_message.author),
                        )

                        message = await self.api.upsert_message(
                            org_id=self.org_id,
                            system="discord",
                            message_id=str(discord_message.id),
                            component_id=str(channel.id),
                            author_external_id=str(discord_message.author.id),
                            content=discord_message.content,
                            has_attachments=bool(discord_message.attachments),
                            reply_to_message_id=str(discord_message.reference.message_id) if discord_message.reference else None,
                            created_at=discord_message.created_at,
                            edited_at=discord_message.edited_at,
                            raw_data={
                                "discord_message_id": discord_message.id,
                                "channel_id": channel.id,
                                "author_id": discord_message.author.id,
                                "author_name": str(discord_message.author),
                                "type": str(discord_message.type),
                                "attachments": [
                                    {
                                        "id": att.id,
                                        "filename": att.filename,
                                        "size": att.size,
                                        "url": att.url,
                                    }
                                    for att in discord_message.attachments
                                ],
                                "embeds": len(discord_message.embeds),
                                "mentions": [str(user.id) for user in discord_message.mentions],
                                "reactions": [
                                    {"emoji": str(reaction.emoji), "count": reaction.count}
                                    for reaction in discord_message.reactions
                                ],
                            },
                        )
                        synced_messages.append(message)

                        # Sync reactions
                        for reaction in discord_message.reactions:
                            async for user in reaction.users():
                                if not user.bot:  # Skip bot reactions
                                    await self.api.add_reaction(
                                        message_id=str(discord_message.id),
                                        reaction=str(reaction.emoji),
                                        member_external_id=str(user.id),
                                        system="discord",
                                        created_at=discord_message.created_at,  # Approximate
                                    )

                    # Sync thread messages
                    threads = [t async for t in channel.archived_threads(limit=None)]
                    active_threads = channel.threads

                    for thread in [*threads, *active_threads]:
                        print(f"Processing thread: {thread.name}")
                        async for discord_message in thread.history(limit=limit_per_channel):
                            # Ensure member exists
                            author_member_id = await self.api.ensure_member_for_discord(
                                org_id=self.org_id,
                                discord_user_id=str(discord_message.author.id),
                                display_name=str(discord_message.author),
                            )

                            message = await self.api.upsert_message(
                                org_id=self.org_id,
                                system="discord",
                                message_id=str(discord_message.id),
                                component_id=str(thread.id),
                                author_external_id=str(discord_message.author.id),
                                content=discord_message.content,
                                has_attachments=bool(discord_message.attachments),
                                reply_to_message_id=str(discord_message.reference.message_id) if discord_message.reference else None,
                                created_at=discord_message.created_at,
                                edited_at=discord_message.edited_at,
                                raw_data={
                                    "discord_message_id": discord_message.id,
                                    "channel_id": channel.id,
                                    "thread_id": thread.id,
                                    "author_id": discord_message.author.id,
                                    "author_name": str(discord_message.author),
                                    "type": str(discord_message.type),
                                    "is_thread": True,
                                },
                            )
                            synced_messages.append(message)

                            # Sync reactions for thread messages
                            for reaction in discord_message.reactions:
                                async for user in reaction.users():
                                    if not user.bot:
                                        await self.api.add_reaction(
                                            message_id=str(discord_message.id),
                                            reaction=str(reaction.emoji),
                                            member_external_id=str(user.id),
                                            system="discord",
                                            created_at=discord_message.created_at,
                                        )

                print(f"Synced {len(synced_messages)} Discord messages")

            except Exception as e:
                print(f"Error syncing Discord messages: {str(e)}")
                raise
            finally:
                await client.close()

        await client.start(self.token)
        return synced_messages

    async def full_discord_sync(self, message_limit_per_channel: Optional[int] = None) -> Dict[str, int]:
        """
        Perform a full Discord sync (channels + messages).

        Args:
            message_limit_per_channel: Maximum messages per channel/thread

        Returns:
            Dict with sync statistics
        """
        print("Starting full Discord sync...")

        # Sync components first
        components = await self.sync_discord_channels()

        # Then sync messages
        messages = await self.sync_discord_messages(message_limit_per_channel)

        stats = {
            "components_synced": len(components),
            "messages_synced": len(messages),
        }

        print(f"Full Discord sync completed: {stats}")
        return stats


class DataFrameLoader:
    """Load data from pandas DataFrames into SQLAlchemy ORM models."""

    def __init__(self, api: BrainCoreAPI):
        """Initialize with BrainCoreAPI instance."""
        self.api = api

    async def load_messages_from_dataframe(
        self,
        df: pd.DataFrame,
        org_id: str,
        system: str = "discord",
        batch_size: int = 1000,
    ) -> int:
        """
        Load messages from a pandas DataFrame.

        Args:
            df: DataFrame with message data
            org_id: Organization identifier
            system: System name
            batch_size: Number of records to process at once

        Returns:
            Number of messages loaded

        Expected DataFrame columns:
            - message_id: Unique message identifier
            - component_id: Channel/thread identifier
            - author_external_id: Author's external ID
            - content: Message content
            - created_at_ts: Creation timestamp
            - edited_at_ts: Edit timestamp (optional)
        """
        total_loaded = 0

        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i + batch_size]
            print(f"Loading batch {i//batch_size + 1}: {len(batch_df)} messages")

            for _, row in batch_df.iterrows():
                try:
                    # Ensure author exists
                    if pd.notna(row.get("author_external_id")):
                        await self.api.ensure_member_for_discord(
                            org_id=org_id,
                            discord_user_id=str(row["author_external_id"]),
                            display_name=row.get("discord_username"),
                        )

                    # Create message
                    await self.api.upsert_message(
                        org_id=org_id,
                        system=system,
                        message_id=str(row["message_id"]),
                        component_id=str(row["component_id"]),
                        author_external_id=str(row["author_external_id"]),
                        content=row.get("content"),
                        has_attachments=bool(row.get("has_attachments", False)),
                        reply_to_message_id=str(row["reply_to_message_id"]) if pd.notna(row.get("reply_to_message_id")) else None,
                        created_at=pd.to_datetime(row["created_at_ts"]) if pd.notna(row.get("created_at_ts")) else None,
                        edited_at=pd.to_datetime(row["edited_at_ts"]) if pd.notna(row.get("edited_at_ts")) else None,
                    )
                    total_loaded += 1

                except Exception as e:
                    print(f"Error loading message {row.get('message_id')}: {str(e)}")
                    continue

        print(f"Total messages loaded: {total_loaded}")
        return total_loaded