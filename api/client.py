# custom_tools/api/websocket_client.py
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from pydantic import BaseModel
import httpx

from llmgine.api.services.session_service import SessionStatus

from api.config import WebSocketConfig

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"

class WebSocketMessage(BaseModel):
    """Standardized WebSocket message format"""
    type: str
    data: Dict[str, Any]

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    created_at: str

class WebSocketAPIClient:
    """WebSocket-based API client for backend communication"""

    def __init__(self):
        self.websocket: Optional[Any] = None  # Use Any to avoid attribute/type errors
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.session_info: Optional[SessionInfo] = None
        self.message_handlers: Dict[str, List[Callable[..., None]]] = {}
        self.response_queue: asyncio.Queue[WebSocketMessage] = asyncio.Queue()
        self._monitor_task: Optional[asyncio.Task[None]] = None
        self.config = WebSocketConfig.from_env()
        self.client = httpx.AsyncClient()
        self.session_id: Optional[str] = None
        
    async def create_session(self) -> SessionInfo:
        """Create a new session with the backend"""
        try:
            logger.info(f"Attempting to create session at: {self.config.base_url}/api/sessions")
            
            # Create session via HTTP API with better timeout and error handling
            response = await self.client.post(
                f"{self.config.base_url}/api/sessions",
                follow_redirects=True,
                timeout=30.0  # 30 second timeout
            )
            
            logger.info(f"HTTP response status: {response.status_code}")
            
            response_data = response.json()
            logger.info(f"Response data: {response_data}")
            
            if response_data.get("status") != "success":
                raise Exception(f"Failed to create session: {response_data.get('message', 'Unknown error')}")
            
            self.session_id = response_data["session_id"]
            logger.info(f"Session created via HTTP: {self.session_id}")
            
            # Connect to WebSocket with the session ID
            ws_url = f"{self.config.ws_url}/api/sessions/{self.session_id}/ws"
            logger.info(f"Connecting to WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            self.state = ConnectionState.CONNECTED
            
            logger.info(f"WebSocket connected to: {ws_url}")
            
            # Start monitoring BEFORE waiting for the connected message
            await self.start_monitoring()
            
            # Wait for the backend's "connected" confirmation
            response = await self._wait_for_response("connected", timeout=self.config.message_timeout)
            print(f"Received response: {response}")
            
            if response and response.data.get("status") == SessionStatus.RUNNING.value:
                self.session_info = SessionInfo(
                    session_id=self.session_id,
                    created_at=datetime.now().isoformat()
                )
                logger.info(f"Session fully established: {self.session_id}")
                return self.session_info
            else:
                # Clean up if connection confirmation failed
                await self._disconnect()
                raise Exception("Failed to receive connection confirmation from backend")
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout creating session: {e}")
            raise Exception(f"Timeout: Backend server not responding. Is it running?")
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise Exception(f"Connection error: Cannot reach backend server. Is it running on {self.config.base_url}?")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            # Clean up on error
            await self._disconnect()
            raise

    
    async def use_websocket(self, message_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message through WebSocket and wait for response"""
        if not self.session_info:
            raise Exception("No active session. Call create_session() first.")
        
        if self.state != ConnectionState.CONNECTED:
            raise Exception("WebSocket not connected. Call connect_websocket() first.")
        
        try:
            message = WebSocketMessage(
                type=message_type,
                data=data,
            )
            
            await self._send_message(message)
            
            # Wait for response
            response = await self._wait_for_response(f"{message_type}_response", timeout=self.config.message_timeout)
            return response.data if response else None
            
        except Exception as e:
            logger.error(f"Error using WebSocket: {e}")
            raise
    
    async def start_monitoring(self):
        """Start monitoring WebSocket for responses"""
        if self._monitor_task and not self._monitor_task.done():
            return
        
        self._monitor_task = asyncio.create_task(self._monitor_websocket())
        logger.info("WebSocket monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring WebSocket"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket monitoring stopped")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    async def close(self):
        """Close the WebSocket connection and cleanup"""
        await self.stop_monitoring()
        await self._disconnect()
        logger.info("WebSocket client closed")
    

    async def _disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.state = ConnectionState.DISCONNECTED
        logger.info("WebSocket disconnected")
    
    async def _send_message(self, message: WebSocketMessage):
        """Send a message through WebSocket"""
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        message_json = json.dumps({
            "type": message.type,
            "data": message.data,
        })
        
        await self.websocket.send(message_json)
        logger.debug(f"Sent message: {message.type}")
    
    async def _monitor_websocket(self):
        """Monitor WebSocket for incoming messages"""
        while self.state == ConnectionState.CONNECTED:
            try:
                if not self.websocket:
                    break
                
                message_json = await self.websocket.recv()
                message_data = json.loads(message_json)
                
                # Parse message
                message = WebSocketMessage(
                    type=message_data.get("type", "unknown"),
                    data=message_data.get("data", {}),
                )
                
                # Handle message
                await self._handle_message(message)
                
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                await self._handle_reconnection()
                break
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                await self._handle_reconnection()
                break
            except Exception as e:
                logger.error(f"Error monitoring WebSocket: {e}")
                break
    
    async def _handle_message(self, message: WebSocketMessage):
        """Handle incoming message"""
        logger.debug(f"Received message: {message.type}")
        
        # Add to response queue for waiting operations
        await self.response_queue.put(message)
        
        # Call registered handlers
        if message.type in self.message_handlers:
            for handler in self.message_handlers[message.type]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
    
    async def _wait_for_response(self, expected_type: str, timeout: float = 30.0) -> Optional[WebSocketMessage]:
        """Wait for a specific response type"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.warning(f"Timeout waiting for response: {expected_type}")
                    return None
                
                # Try to get message from queue
                try:
                    message = await asyncio.wait_for(self.response_queue.get(), timeout=1.0)
                    if message.type == expected_type:
                        return message
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    async def _handle_reconnection(self):
        """Handle WebSocket reconnection"""
        self.state = ConnectionState.RECONNECTING
        
        while self.state == ConnectionState.RECONNECTING:
            try:
                logger.info(f"Attempting to reconnect in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)
                
                await self._connect()
                if self.state == ConnectionState.CONNECTED:
                    logger.info("Reconnected successfully")
                    # Restart monitoring
                    await self.start_monitoring()
                    break
                    
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID"""
        import uuid
        return str(uuid.uuid4())