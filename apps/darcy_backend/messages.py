"""
This module contains custom message types for the Darcy backend.
All messages except create session request must include a session_id field.

Usage:
    - GetEngineTypesRequest: Request to get engine types
    - GetEngineTypesResponse: Response to get engine types
    - LinkEngineRequest: Request to link an engine
    - LinkEngineResponse: Response to link an engine
    - UseEngineRequest: Request to use an engine
    - UseEngineResponse: Response to use an engine
"""

from typing import List
from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.core.extensibility import CustomMessageMixin
from llmgineAPI.models.websocket import MESSAGE_ID

# ================================ CUSTOM MESSAGE TYPES ================================

class GetEngineTypesRequest(WSMessage, CustomMessageMixin):
    """Custom message for getting engine types."""

    def __init__(self, session_id: str):
        super().__init__(
            type="get_engine_types",
            data={"session_id": session_id}
        )

class GetEngineTypesResponse(WSResponse):
    """Custom response for getting engine types."""

    def __init__(self, engine_types: List[str], session_id: str, message_id: MESSAGE_ID):
        super().__init__(
            type="get_engine_types_res",
            message_id=message_id,
            data={"engine_types": engine_types,
                  "session_id": session_id}
        )

class LinkEngineRequest(WSMessage, CustomMessageMixin):
    """Custom message for linking an engine."""
    
    def __init__(self, engine_type: str, session_id: str):
        super().__init__(
            type="link_engine",
            data={
                "engine_type": engine_type,
                "session_id": session_id
            }
        )

class LinkEngineResponse(WSResponse):
    """Custom response for linking an engine."""
    
    def __init__(self, engine_id: str, session_id: str, message_id: MESSAGE_ID):
        super().__init__(
            type="link_engine_res",
            message_id=message_id,
            data={
                "engine_id": engine_id,
                "session_id": session_id
            }
        )

class UseEngineRequest(WSMessage, CustomMessageMixin):
    """Custom message for using a registered engine."""
    
    def __init__(self, prompt: str, session_id: str):
        super().__init__(
            type="use_engine",
            data={"prompt": prompt,
                  "session_id": session_id}
        )

class UseEngineResponse(WSResponse):
    """Custom response for engine usage."""
    
    def __init__(self, result: str, session_id: str, message_id: MESSAGE_ID):
        super().__init__(
            type="use_engine_res",
            message_id=message_id,
            data={
                "result": result,
                "session_id": session_id
            }
        )
