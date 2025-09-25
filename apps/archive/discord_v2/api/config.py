# config/websocket_config.py
import os
from dataclasses import dataclass

@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connections"""
    base_url: str
    ws_url: str
    reconnect_delay: float
    max_reconnect_delay: float
    message_timeout: float
    
    @classmethod
    def from_env(cls) -> 'WebSocketConfig':
        """Create config from environment variables"""
        return cls(
            base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
            ws_url=os.getenv("BACKEND_WS_URL", "ws://localhost:8000"),
            reconnect_delay=float(os.getenv("WEBSOCKET_RECONNECT_DELAY", "1.0")),
            max_reconnect_delay=float(os.getenv("WEBSOCKET_MAX_RECONNECT_DELAY", "30.0")),
            message_timeout=float(os.getenv("WEBSOCKET_MESSAGE_TIMEOUT", "30.0"))
        )
    

def main():
    config = WebSocketConfig.from_env()

    print(config)

if __name__ == "__main__":
    main()