from typing import Optional
import logging

from llmgineAPI.models.websocket import WSError, WSErrorCode, WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler
from llmgine.llm import SessionID
from llmgineAPI.services.engine_service import EngineService
from fastapi import WebSocket

from engines import ENGINE_TYPES
from engines.fact_processing_engine import FactProcessingEngine
from engines.notion_crud_engine_v3 import NotionCRUDEngineV3

from messages import GetEngineTypesRequest, GetEngineTypesResponse, LinkEngineRequest, LinkEngineResponse, UseEngineRequest, UseEngineResponse

logger = logging.getLogger(__name__)


# ================================ CUSTOM HANDLERS ================================

class LinkEngineHandler(BaseHandler):
    """Handler for linking an engine."""
    
    @property
    def message_type(self) -> str:
        return "link_engine"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return LinkEngineRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle engine linking."""
        try:
            engine_type = message.data.get("engine_type")

            # Check if engine type is provided
            if not engine_type:
                return WSError(
                    code=WSErrorCode.INVALID_ENGINE_TYPE,
                    message="No engine type provided",
                    message_id=message.message_id
                )
            
            # Create engine based on type
            engine = None
            if engine_type in ENGINE_TYPES:
                engine = ENGINE_TYPES[engine_type](session_id=session_id)
                # Initialize the engine (register tools, etc.) if it has an initialize method
                if hasattr(engine, 'initialize'):
                    await engine.initialize()
            else:
                return WSError(
                    code=WSErrorCode.INVALID_ENGINE_TYPE,
                    message=f"Unknown engine type: {engine_type}",
                    message_id=message.message_id
                )

            
            # Register engine with engine service
            engine_service = EngineService()
            engine_id = engine_service.create_engine(engine)
            
            if engine_id:
                # Register engine to session
                engine_service.register_engine(session_id, engine_id)
                logger.info(f"Linked engine {engine_id} for session {session_id}")
                
                return LinkEngineResponse(
                    engine_id=str(engine_id),
                    message_id=message.message_id,
                    session_id=str(session_id)
                )
            else:
                return WSError(
                    code=WSErrorCode.ENGINE_CREATION_FAILED,
                    message="Failed to create engine: maximum engines reached",
                    message_id=message.message_id,
                )
                
        except Exception as e:
            logger.error(f"Error linking engine: {e}")
            return WSError(
                code=WSErrorCode.ENGINE_CREATION_FAILED,
                message=f"Error linking engine: {str(e)}",
                message_id=message.message_id,
            )


class UseEngineHandler(BaseHandler):
    """Handler for using registered engines."""
    
    @property
    def message_type(self) -> str:
        return "use_engine"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return UseEngineRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle engine usage request."""
        try:
            prompt = message.data["prompt"]
            
            # Get registered engine for this session
            engine_service = EngineService()
            engine = engine_service.get_registered_engine(session_id)
            
            if not engine:
                return WSError(
                    code=WSErrorCode.ENGINE_NOT_FOUND,
                    message="No engine registered for this session",
                    message_id=message.message_id
                )
            
            # Update engine interaction time
            engine_service.update_engine_last_interaction_at(engine.engine_id)
            
            # Use the engine based on type
            if isinstance(engine, FactProcessingEngine):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    result=result,
                    message_id=message.message_id,
                    session_id=str(session_id)
                )
                    
            elif isinstance(engine, NotionCRUDEngineV3):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    result=result,
                    message_id=message.message_id,
                    session_id=str(session_id)
                )
            else:
                return WSError(
                    code=WSErrorCode.ENGINE_NOT_FOUND,
                    message="Error in engine registration",
                    message_id=message.message_id
                )
                
        except Exception as e:
            logger.error(f"Error using engine: {e}")
            return WSError(
                code=WSErrorCode.ENGINE_CREATION_FAILED,
                message=f"Error using engine: {str(e)}",
                message_id=message.message_id
            )

class GetEngineTypesHandler(BaseHandler):

    @property
    def message_type(self) -> str:
        return "get_engine_types"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return GetEngineTypesRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle engine types request."""  
        try:
            engine_types = list(ENGINE_TYPES.keys())
            return GetEngineTypesResponse(engine_types, str(session_id), message.message_id)
        except Exception as e:
            logger.error(f"Error getting engine types: {e}")
            return WSError(
                code=WSErrorCode.ENGINE_CREATION_FAILED,
                message=f"Error getting engine types: {str(e)}",
                message_id=message.message_id
            )
