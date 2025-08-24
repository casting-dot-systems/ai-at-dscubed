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
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "channel_created_at": channel.created_at.isoformat(),
                    })
                
                print("Channel fetch completed successfully")
                
            except Exception as e:
                print(f"Error fetching channels: {str(e)}")
                raise
            finally:
                # Properly close the client and clean up connections
                try:
                    await client.close()
                    # Give some time for connections to close properly
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during client cleanup: {cleanup_error}")
        
        try:
            await client.start(self.token)
        except Exception as e:
            print(f"Error starting Discord client: {str(e)}")
            raise
        finally:
            # Ensure client is closed even if start fails
            if not client.is_closed():
                try:
                    await client.close()
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during final client cleanup: {cleanup_error}")
        
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
                            "is_thread": False
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
                                "is_thread": True
                            })
                
                print("Chat history fetch completed successfully")
                
            except Exception as e:
                print(f"Error fetching chat history: {str(e)}")
                raise
            finally:
                # Properly close the client and clean up connections
                try:
                    await client.close()
                    # Give some time for connections to close properly
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during client cleanup: {cleanup_error}")
        
        try:
            await client.start(self.token)
        except Exception as e:
            print(f"Error starting Discord client: {str(e)}")
            raise
        finally:
            # Ensure client is closed even if start fails
            if not client.is_closed():
                try:
                    await client.close()
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during final client cleanup: {cleanup_error}")
        
        return messages_data
    
    # Extract
    async def fetch_discord_reactions(self, limit_per_channel: int = 100) -> List[Dict[str, Any]]:
        """Fetch reactions from messages and return as list of dictionaries."""
        client = self.create_client()
        reactions_data = []
        
        @client.event
        async def on_ready():
            try:
                print("Fetching reactions...")
                guild = client.get_guild(self.guild_id)
                if not guild:
                    raise ValueError(f"Guild with ID {self.guild_id} not found")
                
                print(f"Found {len(guild.text_channels)} text channels")
                
                channel_count = 0
                for channel in guild.text_channels:
                    channel_count += 1
                    print(f"[{channel_count}/{len(guild.text_channels)}] Processing reactions in #{channel.name}")
                    
                    message_count = 0
                    # Fetch reactions from channel messages
                    async for message in channel.history(limit=limit_per_channel):
                        message_count += 1
                        if message_count % 20 == 0:
                            print(f"  Processed {message_count} messages, found {len(reactions_data)} reactions so far")
                        
                        for reaction in message.reactions:
                            async for user in reaction.users():
                                reactions_data.append({
                                    "message_id": message.id,
                                    "reaction_id": f"{message.id}_{reaction.emoji}_{user.id}",
                                    "reaction": str(reaction.emoji),
                                    "discord_username": str(user),
                                    "discord_user_id": user.id,
                                })
                    
                    print(f"  #{channel.name}: {message_count} messages processed")
                    
                    # Skip threads for now to speed up testing
                    # TODO: Re-enable thread processing after confirming main channels work
                    
                print(f"Reactions fetch completed! Total reactions: {len(reactions_data)}")
                
            except Exception as e:
                print(f"Error fetching reactions: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
            finally:
                # Properly close the client and clean up connections
                try:
                    await client.close()
                    # Give some time for connections to close properly
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during client cleanup: {cleanup_error}")
        
        try:
            await client.start(self.token)
        except Exception as e:
            print(f"Error starting Discord client: {str(e)}")
            raise
        finally:
            # Ensure client is closed even if start fails
            if not client.is_closed():
                try:
                    await client.close()
                    import asyncio
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    print(f"Warning: Error during final client cleanup: {cleanup_error}")
        
        return reactions_data
    
    # Transform
    async def parse_discord_data(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform raw Discord data into a DataFrame."""
        try:
            return pd.DataFrame(raw_data)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error transforming Discord data: {str(e)}")
            raise 
