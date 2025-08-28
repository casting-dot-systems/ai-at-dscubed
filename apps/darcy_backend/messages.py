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
from pydantic import BaseModel

# ================================ CUSTOM MESSAGE TYPES ================================


# ============================Frontend -> Backend============================
class GetEngineTypesRequest(WSMessage):
    """Custom message for getting engine types."""
    
    class GetEngineTypesRequestData(BaseModel):
        session_id: str
    
    type: str = "get_engine_types"
    message_id: str
    data: GetEngineTypesRequestData

class GetEngineTypesResponse(WSResponse):
    """Custom response for getting engine types."""

    class GetEngineTypesResponseData(BaseModel):
        engine_types: List[str]
        session_id: str

    type: str = "get_engine_types_res"
    message_id: str
    data: GetEngineTypesResponseData



class LinkEngineRequest(WSMessage):
    """Custom message for linking an engine."""

    class LinkEngineRequestData(BaseModel):
        engine_type: str
        session_id: str

    type: str = "link_engine"
    message_id: str
    data: LinkEngineRequestData

class LinkEngineResponse(WSResponse):
    """Custom response for linking an engine."""

    class LinkEngineResponseData(BaseModel):
        engine_id: str
        session_id: str

    type: str = "link_engine_res"
    message_id: str
    data: LinkEngineResponseData



class UseEngineRequest(WSMessage):
    """Custom message for using a registered engine."""

    class UseEngineRequestData(BaseModel):
        prompt: str
        session_id: str
        channel_id: str

    type: str = "use_engine"
    message_id: str
    data: UseEngineRequestData

class UseEngineResponse(WSResponse):
    """Custom response for engine usage."""

    class UseEngineResponseData(BaseModel):
        result: str
        session_id: str

    type: str = "use_engine_res"
    message_id: str
    data: UseEngineResponseData

# ============================Backend -> Frontend============================
# Server-initiated confirmation messages
class ConfirmationServerRequest(WSMessage):
    """Server-initiated confirmation request."""

    class ConfirmationServerRequestData(BaseModel):
        request_type: str = "confirmation"
        prompt: str
        session_id: str
        channel_id: str

    type: str = "server_request"
    message_id: str
    server_initiated: bool = True
    data: ConfirmationServerRequestData


class ConfirmationServerResponse(WSResponse):
    """Response to server-initiated confirmation."""

    class ConfirmationServerResponseData(BaseModel):
        response_type: str = "confirmation"
        confirmed: bool
        session_id: str

    type: str = "server_response"
    message_id: str
    data: ConfirmationServerResponseData