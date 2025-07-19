# custom_tools/api/api_service.py
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from .client import WebSocketAPIClient, WebSocketMessage, SessionInfo

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    SESSION_CREATED = "session_created"
    SESSION_CLOSED = "session_closed"
    MESSAGE_RECEIVED = "message_received"
    CONNECTION_STATUS = "connection_status"
    ERROR = "error"

@dataclass
class Notification:
    """Notification sent to applications"""
    type: NotificationType
    data: Dict[str, Any]
    timestamp: float

class APIService:
    """Service layer that manages WebSocket connections and notifications"""
    
    def __init__(self, base_url: str = "ws://localhost:8000/ws"):
        self.client = WebSocketAPIClient(base_url)
        self.notification_handlers: List[Callable] = []
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._notification_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the API service"""
        # Register internal message handlers
        self.client.register_message_handler("session_created", self._handle_session_created)
        self.client.register_message_handler("session_closed", self._handle_session_closed)
        self.client.register_message_handler("error", self._handle_error)
        
        # Start notification processing
        await self._start_notification_processor()
        
        logger.info("API Service initialized")
    
    async def create_session(self, session_data: Optional[Dict[str, Any]] = None) -> SessionInfo:
        """Create a new session"""
        try:
            session_info = await self.client.create_session(session_data)
            
            # Send notification
            await self._send_notification(
                NotificationType.SESSION_CREATED,
                {"session_id": session_info.session_id, "session_data": session_data}
            )
            
            return session_info
            
        except Exception as e:
            await self._send_notification(
                NotificationType.ERROR,
                {"error": f"Failed to create session: {str(e)}"}
            )
            raise
    
    async def connect_websocket(self) -> bool:
        """Connect to WebSocket"""
        try:
            success = await self.client.connect_websocket()
            
            await self._send_notification(
                NotificationType.CONNECTION_STATUS,
                {"connected": success}
            )
            
            if success:
                await self.client.start_monitoring()
            
            return success
            
        except Exception as e:
            await self._send_notification(
                NotificationType.ERROR,
                {"error": f"Failed to connect: {str(e)}"}
            )
            raise
    
    async def use_websocket(self, message_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send message through WebSocket"""
        try:
            response = await self.client.use_websocket(message_type, data)
            
            # Send notification about message sent
            await self._send_notification(
                NotificationType.MESSAGE_RECEIVED,
                {
                    "message_type": message_type,
                    "data": data,
                    "response": response
                }
            )
            
            return response
            
        except Exception as e:
            await self._send_notification(
                NotificationType.ERROR,
                {"error": f"Failed to send message: {str(e)}"}
            )
            raise
    
    def register_notification_handler(self, handler: Callable[[Notification], None]):
        """Register a handler for notifications"""
        self.notification_handlers.append(handler)
        logger.info(f"Registered notification handler: {handler}")
    
    async def close(self):
        """Close the API service"""
        await self._stop_notification_processor()
        await self.client.close()
        logger.info("API Service closed")
    
    # Private methods
    async def _start_notification_processor(self):
        """Start processing notifications"""
        if self._notification_task and not self._notification_task.done():
            return
        
        self._notification_task = asyncio.create_task(self._process_notifications())
        logger.info("Notification processor started")
    
    async def _stop_notification_processor(self):
        """Stop processing notifications"""
        if self._notification_task:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
        logger.info("Notification processor stopped")
    
    async def _process_notifications(self):
        """Process notifications and send to handlers"""
        while True:
            try:
                notification = await self.notification_queue.get()
                
                # Send to all registered handlers
                for handler in self.notification_handlers:
                    try:
                        handler(notification)
                    except Exception as e:
                        logger.error(f"Error in notification handler: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notifications: {e}")
    
    async def _send_notification(self, notification_type: NotificationType, data: Dict[str, Any]):
        """Send a notification"""
        notification = Notification(
            type=notification_type,
            data=data,
            timestamp=asyncio.get_event_loop().time()
        )
        
        await self.notification_queue.put(notification)
    
    # Internal message handlers
    async def _handle_session_created(self, message: WebSocketMessage):
        """Handle session created message"""
        await self._send_notification(
            NotificationType.SESSION_CREATED,
            message.data
        )
    
    async def _handle_session_closed(self, message: WebSocketMessage):
        """Handle session closed message"""
        await self._send_notification(
            NotificationType.SESSION_CLOSED,
            message.data
        )
    
    async def _handle_error(self, message: WebSocketMessage):
        """Handle error message"""
        await self._send_notification(
            NotificationType.ERROR,
            message.data
        )