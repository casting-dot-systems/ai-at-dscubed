"""
This module handles interactions with the darcy_backend API for the discord bot.

Responsibilities include:
- WebSocket API communication
- Engine linking and management via API
- Message processing through backend API
- Session management coordination
"""

import logging
from typing import Optional, List

from llmgine.llm import SessionID, EngineID

from .config import DiscordBotConfig
from .session_manager import SessionData, SessionManager, SessionStatus
from .api.client import WebSocketAPIClient

logger = logging.getLogger(__name__)


class EngineManager:
    def __init__(self, config: DiscordBotConfig, session_manager: SessionManager):
        self.config: DiscordBotConfig = config
        self.session_manager: SessionManager = session_manager
        self.api_client: Optional[WebSocketAPIClient] = None

    async def initialize_api_client(self):
        """Initialize and connect the WebSocket API client."""
        if not self.api_client:
            self.api_client = WebSocketAPIClient()
            await self.api_client.connect_websocket()
            logger.info(f"API client initialized with session: {self.api_client.app_id}")
        return self.api_client
    
    async def get_available_engines(self, session_id: SessionID) -> List[str]:
        """Get list of available engine types from the backend."""
        if not self.api_client:
            await self.initialize_api_client()
            assert self.api_client is not None
        
        try:
            response = await self.api_client.use_websocket(
                "get_engine_types", 
                {"session_id": session_id}
            )
            if response and response.data.get("engine_types"):
                return response.data["engine_types"]
            else:
                logger.error("Failed to get engine types from backend")
                return []
        except Exception as e:
            logger.error(f"Error getting engine types: {e}")
            return []
    
    async def link_engine(self, session_id: SessionID, user_id: str, engine_type: str = "notion_crud") -> bool:
        """Link an engine of the specified type."""
        if not self.api_client:
            await self.initialize_api_client()
            assert self.api_client is not None

        # Update session status to processing
        await self.session_manager.update_session_status(
            user_id, SessionStatus.INITIATING_ENGINE, "Linking engine..."
        )

        try:
            response = await self.api_client.use_websocket(
                "link_engine",
                {
                    "engine_type": engine_type,
                    "session_id": session_id
                }
            )
            if response and response.data.get("engine_id"):
                self.session_manager.active_sessions[user_id].engine_id = EngineID(response.data["engine_id"])
                logger.info(f"Successfully linked engine: {response.data["engine_id"]}")
                return True
            else:
                raise Exception("Failed to link engine")
        except Exception as e:
            logger.error(f"Error linking engine: {e}")
            await self.session_manager.update_session_status(
                user_id, SessionStatus.ERROR, f"Error: {str(e)}"
            )
            return False

    async def process_user_message(self, prompt: str, session_id: SessionID, user_id: str, channel_id: str) -> str:
        """Process a user message through the linked engine."""
        # Ensure we have an API client and linked engine
        if not self.api_client:
            await self.initialize_api_client()
            assert self.api_client is not None
        
        if user_id not in self.session_manager.active_sessions:
            return "Session not found. Please try again later."
        
        session_data : SessionData = self.session_manager.active_sessions[user_id]
        if session_data.engine_id is None:
            success = await self.link_engine(session_id, user_id)
            if not success:
                return "Failed to link engine. Please try again later."

        try:
            # Update session status to processing
            await self.session_manager.update_session_status(
                user_id, SessionStatus.PROCESSING, "Processing your request..."
            )
            
            # Send prompt to the linked engine
            response = await self.api_client.use_websocket(
                "use_engine",
                {
                    "prompt": prompt,
                    "session_id": session_id,
                    "channel_id": channel_id
                }
            )
            
            if response and response.data.get("result"):
                # Update session status to idle
                await self.session_manager.update_session_status(
                    user_id, SessionStatus.IDLE, "Ready"
                )
                return response.data["result"]
            else:
                logger.error("No result received from engine")
                return "I encountered an issue processing your request. Please try again."
                
        except Exception as e:
            logger.error(f"Error processing message through engine: {e}")
            await self.session_manager.update_session_status(
                user_id, SessionStatus.ERROR, f"Error: {str(e)}"
            )
            return "I encountered an error processing your request. Please try again later."

    async def cleanup(self):
        """Clean up resources when shutting down."""
        if self.api_client:
            await self.api_client.close()
            logger.info("Engine manager cleaned up")