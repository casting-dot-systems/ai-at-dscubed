# custom_tools/api/websocket_client.py
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import uuid
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import httpx

from llmgineAPI.models.websocket import WSMessage, WSResponse

from .config import WebSocketConfig

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"

class WebSocketAPIClient:
    """WebSocket-based API client for backend communication"""

    def __init__(self):
        self.websocket: Optional[Any] = None  # Use Any to avoid attribute/type errors
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.response_queue: asyncio.Queue[WSResponse] = asyncio.Queue()
        self._monitor_task: Optional[asyncio.Task[None]] = None
        self.config = WebSocketConfig.from_env()
        self.client = httpx.AsyncClient()
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._server_message_handlers: Dict[str, Callable] = {}
        self.app_id: Optional[str] = None

    async def connect_websocket(self) -> Optional[str]:
        """Connect to the WebSocket"""
        try:

            ws_url = f"{self.config.ws_url}/api/ws"
            logger.info(f"Connecting to WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            self.state = ConnectionState.CONNECTED
            
            logger.info(f"WebSocket connected to: {ws_url}")
            
            # Start monitoring BEFORE waiting for the connected message
            await self.start_monitoring()
            
            # Wait for the backend's "connected" confirmation
            response = await self._wait_for_response("connected", expected_message_id=None, timeout=self.config.message_timeout)
            print(f"Received response: {response}")
            
            if response and response.data.get("status") == "connected":
                self.app_id = response.data.get("app_id")
                logger.info(f"Session fully established: {self.app_id}")
                return self.app_id
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

    
    async def use_websocket(self, message_type: str, data: Dict[str, Any]) -> Optional[WSResponse]:
        """Send a message through WebSocket and wait for response"""

        if self.state != ConnectionState.CONNECTED:
            raise Exception("WebSocket not connected. Call connect_websocket() first.")
        
        try:
            if message_type == "create_session":
                data["app_id"] = self.app_id

            message = WSMessage(
                type=message_type,
                message_id=str(uuid.uuid4()),
                data=data,
            )
            print(f"Sending message: {message}")
            await self._send_message(message)
            print(f"Waiting for response: {message_type}_res")
            print(f"Message ID: {data.get('message_id')}")
            # Wait for response
            response = await self._wait_for_response(f"{message_type}_res", message.message_id, timeout=self.config.message_timeout)
            print(f"Received response: {response}")
            return response if response else None
            
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

    
    async def close(self):
        """Close the WebSocket connection and cleanup"""
        await self.stop_monitoring()
        await self._disconnect()
        logger.info("WebSocket client closed")
    
    async def _connect(self):
        """Connect to WebSocket"""
        if self.websocket:
            
            # Connect to WebSocket with the session ID
            ws_url = f"{self.config.ws_url}/api/ws"
            
            self.websocket = await websockets.connect(ws_url)
            self.state = ConnectionState.CONNECTED

            await self.start_monitoring()
            response = await self._wait_for_response("connected", expected_message_id=None, timeout=self.config.message_timeout)
            if response and response.type == "connected":
                logger.info("WebSocket connected")
            else:
                raise Exception("Failed to connect to WebSocket")
        else:
            raise Exception("WebSocket not connected")

    async def _disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.state = ConnectionState.DISCONNECTED
        logger.info("WebSocket disconnected")
    
    async def _send_message(self, message: WSMessage):
        """Send a message through WebSocket"""
        if not self.websocket:
            raise Exception("WebSocket not connected")

        
        await self.websocket.send(message.model_dump_json())
        logger.debug(f"Sent message: {message.type}")
    
    async def _monitor_websocket(self):
        """Monitor WebSocket for incoming messages"""
        while self.state == ConnectionState.CONNECTED:
            try:
                if not self.websocket:
                    break
                
                message_json = await self.websocket.recv()
                message_data = json.loads(message_json)
                print(f"Received message: {message_data}")

                # Check if this is a server-initiated message
                if message_data.get("type") == "server_request":
                    await self._handle_server_request(message_data)
                else:
                    # Handle regular response messages
                    await self.response_queue.put(WSResponse(
                        type=message_data.get("type", "unknown"),
                        data=message_data.get("data", {}),
                        message_id=message_data.get("message_id", str(uuid.uuid4()))
                    ))
                    print(f"Response queue: {self.response_queue}")
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                break
            except Exception as e:
                logger.error(f"Error monitoring WebSocket: {e}")
                break
    
    async def _wait_for_response(self, expected_type: str, expected_message_id: Optional[str] = None, timeout: float = 30.0) -> Optional[WSResponse]:
        """Wait for a specific response type"""
        try:
            start_time = asyncio.get_event_loop().time()
            pending_messages : List[WSResponse] = []
            
            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.warning(f"Timeout waiting for response: {expected_type}")
                    # Put back any pending messages we didn't process
                    for msg in pending_messages:
                        await self.response_queue.put(msg)
                    return None
                
                # Try to get message from queue
                try:
                    print(f"Waiting for response type: {expected_type}, message_id: {expected_message_id}")
                    message = await asyncio.wait_for(self.response_queue.get(), timeout=1.0)
                    print(f"Got message: type={message.type}, message_id={message.message_id}")
                    
                    # Check if this is the message we're looking for
                    if message.type == expected_type:
                        # For messages that require specific message_id matching
                        if expected_message_id is not None:
                            if message.message_id == expected_message_id:
                                # Put back any pending messages
                                for msg in pending_messages:
                                    await self.response_queue.put(msg)
                                return message
                            else:
                                # Not the right message_id, add to pending
                                pending_messages.append(message)
                        else:
                            # No message_id requirement, just type match
                            # Put back any pending messages
                            for msg in pending_messages:
                                await self.response_queue.put(msg)
                            return message
                    else:
                        # Not the right type, add to pending
                        pending_messages.append(message)
                        
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            # Put back any pending messages
            for msg in pending_messages:
                await self.response_queue.put(msg)
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
    
    def register_server_message_handler(self, request_type: str, handler: Callable) -> None:
        """Register a handler for server-initiated messages of a specific type."""
        self._server_message_handlers[request_type] = handler
    
    async def _handle_server_request(self, message_data: Dict[str, Any]) -> None:
        """Handle server-initiated requests."""
        try:
            request_type = message_data.get("data", {}).get("request_type")
            
            if request_type in self._server_message_handlers:
                handler = self._server_message_handlers[request_type]
                # Call the handler with the message data
                response_data = await handler(message_data)
                await self.send_server_response(message_data.get("message_id"), response_data)
            else:
                logger.warning(f"No handler registered for server request type: {request_type}")
        except Exception as e:
            logger.error(f"Error handling server request: {e}")
    
    async def send_server_response(self, message_id: str, data: Dict[str, Any]) -> None:
        """Send a response to a server-initiated message."""
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        response_message = WSMessage(
            type="server_response",
            message_id=message_id,
            data=data
        )
        print(f"Sending server response: {response_message}")
        await self._send_message(response_message)
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID"""
        import uuid
        return str(uuid.uuid4())