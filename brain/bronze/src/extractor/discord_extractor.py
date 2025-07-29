import os
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
from discord import Client, Intents, TextChannel
from dotenv import load_dotenv

class DiscordExtractor:
    """
    Discord data extractor that:
    - Fetches channel information
    - Fetches all messages and threads
    - Returns data as pandas DataFrames
    """
    
    def __init__(self):
        """Initialize the Discord extractor with configuration and environment variables."""
        # Disable SSL verification
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Load environment variables
        load_dotenv()
        self.token = os.getenv("BOT_KEY")
        self.guild_id = int(os.getenv("TEST_SERVER_ID", "0"))
        
        if not self.token or not self.guild_id:
            raise ValueError("BOT_KEY and TEST_SERVER_ID must be set in .env file")
        
        # Configure intents
        self.intents = Intents.default()
        self.intents.message_content = True
        self.intents.guilds = True
        self.intents.guild_messages = True
    
    def create_client(self) -> Client:
        """Create and return a new Discord client with configured intents."""
        return Client(intents=self.intents)
    
    def _get_discord_entity_type(self, channel) -> str:
        """Get Discord entity type as a string."""
        # Discord channel type constants
        GUILD_TEXT = 0
        GUILD_VOICE = 2
        GUILD_CATEGORY = 4
        GUILD_NEWS = 5
        GUILD_STAGE_VOICE = 13
        GUILD_FORUM = 15
        
        # Get the channel type from the channel object
        channel_type = getattr(channel, 'type', None)
        
        # Convert Discord enum to string for comparison
        if hasattr(channel_type, 'name'):
            channel_type_str = channel_type.name.lower()
        else:
            channel_type_str = str(channel_type).lower()
        
        # Handle both string and integer types
        if channel_type_str == 'text':
            channel_type_id = GUILD_TEXT
        elif channel_type_str == 'voice':
            channel_type_id = GUILD_VOICE
        elif channel_type_str == 'category':
            channel_type_id = GUILD_CATEGORY
        elif channel_type_str == 'news':
            channel_type_id = GUILD_NEWS
        elif channel_type_str == 'stage':
            channel_type_id = GUILD_STAGE_VOICE
        elif channel_type_str == 'forum':
            channel_type_id = GUILD_FORUM
        else:
            channel_type_id = GUILD_TEXT  # Default fallback
        
        if channel_type_id == GUILD_CATEGORY:
            return 'discord_server'  # Categories are server-level organizational units
        elif channel_type_id == GUILD_FORUM:
            return 'discord_forum'
        elif channel_type_id == GUILD_TEXT:
            return 'discord_channel'
        elif channel_type_id == GUILD_VOICE:
            return 'discord_channel'
        elif channel_type_id == GUILD_NEWS:
            return 'discord_channel'
        elif channel_type_id == GUILD_STAGE_VOICE:
            return 'discord_channel'
        else:
            return 'discord_channel'  # Default fallback
    
    def _get_thread_entity_type(self, thread) -> str:
        """Get Discord thread entity type."""
        return 'discord_thread'
    
    # Extract
    # TODO: find a way to ensure dataframe aligns with the ddl automatically, no need to manually add columns
    async def fetch_discord_channels(self) -> List[Dict[str, Any]]:
        """Fetch all text channels and return as list of dictionaries."""
        client = self.create_client()
        channels_data = []
        
        @client.event
        async def on_ready():
            try:
                print("Fetching channels...")
                guild = client.get_guild(self.guild_id)
                if not guild:
                    raise ValueError(f"Guild with ID {self.guild_id} not found")
                
                # Extract ALL channel types, not just text channels
                all_channels = []
                all_channels.extend(guild.text_channels)
                all_channels.extend(guild.voice_channels)
                all_channels.extend(guild.categories)
                
                # Add forums if available (newer Discord.py versions)
                if hasattr(guild, 'forums'):
                    all_channels.extend(guild.forums)
                
                # Add stage channels if available
                if hasattr(guild, 'stage_channels'):
                    all_channels.extend(guild.stage_channels)
                
                # Add news channels if available (older versions might not have this)
                if hasattr(guild, 'news_channels'):
                    all_channels.extend(guild.news_channels)
                
                print(f"Found {len(all_channels)} total channels:")
                print(f"- Text channels: {len(guild.text_channels)}")
                print(f"- Voice channels: {len(guild.voice_channels)}")
                print(f"- Categories: {len(guild.categories)}")
                if hasattr(guild, 'forums'):
                    print(f"- Forums: {len(guild.forums)}")
                if hasattr(guild, 'stage_channels'):
                    print(f"- Stage channels: {len(guild.stage_channels)}")
                if hasattr(guild, 'news_channels'):
                    print(f"- News channels: {len(guild.news_channels)}")
                
                for channel in all_channels:
                    # Get parent_id - this will be the category_id if channel is in a category, otherwise None
                    parent_id = channel.category_id if hasattr(channel, 'category_id') else None
                    
                    # Get Discord entity type
                    entity_type = self._get_discord_entity_type(channel)
                    
                    channels_data.append({
                        "server_id": guild.id,
                        "server_name": guild.name,
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "channel_created_at": channel.created_at.isoformat(),
                        "parent_id": parent_id,  # Add parent_id information
                        "entity_type": entity_type,  # Add entity type information
                        "ingestion_timestamp": datetime.now().isoformat(),
                    })
                
                print("Channel fetch completed successfully")
                
            except Exception as e:
                print(f"Error fetching channels: {str(e)}")
                raise
            finally:
                await client.close()
        
        await client.start(self.token)
        return channels_data
    
    # Extract
    async def fetch_discord_chat(self) -> List[Dict[str, Any]]:
        """Fetch all messages and threads and return as list of dictionaries."""
        client = self.create_client()
        messages_data = []
        
        @client.event
        async def on_ready():
            try:
                print("Fetching chat history...")
                guild = client.get_guild(self.guild_id)
                if not guild:
                    raise ValueError(f"Guild with ID {self.guild_id} not found")
                
                # Process ALL channel types that can have messages
                message_channels = []
                message_channels.extend(guild.text_channels)
                
                # Add news channels if available
                if hasattr(guild, 'news_channels'):
                    message_channels.extend(guild.news_channels)
                
                # Add forums if available
                if hasattr(guild, 'forums'):
                    message_channels.extend(guild.forums)
                
                print(f"Processing messages from {len(message_channels)} channels with message capability")
                
                for channel in message_channels:
                    print(f"Processing channel: {channel.name} (type: {channel.type})")
                    
                    # Fetch channel messages
                    async for message in channel.history(limit=None):
                        messages_data.append({
                            # "server_id": guild.id,
                            # "server_name": guild.name,
                            "channel_id": channel.id,
                            "channel_name": channel.name,
                            "thread_name": None,
                            "thread_id": None,
                            "message_id": message.id,
                            "discord_username": str(message.author),        # The user's display name
                            "discord_user_id": message.author.id,           # The user's unique ID
                            "content": message.content,
                            "chat_created_at": message.created_at.isoformat(),
                            "chat_edited_at": message.edited_at.isoformat() if message.edited_at else None,
                            "is_thread": False,
                            "ingestion_timestamp": datetime.now().isoformat()
                        })
                    
                    # Fetch and process threads (only for channels that support threads)
                    if hasattr(channel, 'threads') and hasattr(channel, 'archived_threads'):
                        threads = [t async for t in channel.archived_threads(limit=None)]
                        active_threads = channel.threads
                        
                        for thread in [*threads, *active_threads]:
                            print(f"Processing thread: {thread.name}")
                            thread_entity_type = self._get_thread_entity_type(thread)
                            async for message in thread.history(limit=None):
                                messages_data.append({
                                    "channel_id": channel.id,
                                    "channel_name": channel.name,
                                    "thread_name": thread.name,
                                    "thread_id": thread.id,
                                    "message_id": message.id,
                                    "discord_username": str(message.author),        # The user's display name
                                    "discord_user_id": message.author.id,           # The user's unique ID
                                    "content": message.content,
                                    "chat_created_at": message.created_at.isoformat(),
                                    "chat_edited_at": message.edited_at.isoformat() if message.edited_at else None,
                                    "is_thread": True,
                                    "entity_type": thread_entity_type,  # Add entity type for threads
                                    "ingestion_timestamp": datetime.now().isoformat()
                                })
                
                print("Chat history fetch completed successfully")
                
            except Exception as e:
                print(f"Error fetching chat history: {str(e)}")
                raise
            finally:
                await client.close()
        
        await client.start(self.token)
        return messages_data
    
    # Transform
    async def parse_discord_data(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform raw Discord data into a DataFrame."""
        try:
            return pd.DataFrame(raw_data)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error transforming Discord data: {str(e)}")
            raise 
