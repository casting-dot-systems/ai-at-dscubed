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
                
                for channel in guild.text_channels:
                    channels_data.append({
                        "server_id": guild.id,
                        "server_name": guild.name,
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "channel_created_at": channel.created_at.isoformat(),
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
                
                for channel in guild.text_channels:
                    print(f"Processing channel: {channel.name}")
                    
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
                    
                    # Fetch and process threads
                    threads = [t async for t in channel.archived_threads(limit=None)]
                    active_threads = channel.threads
                    
                    for thread in [*threads, *active_threads]:
                        print(f"Processing thread: {thread.name}")
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
