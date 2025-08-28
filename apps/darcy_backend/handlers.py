from typing import Optional, Dict, Any
import logging
import uuid

from llmgine.llm import SessionID
from llmgineAPI.core.messaging_api import MessagingAPIWithEvents
from llmgineAPI.models.websocket import WSError, WSErrorCode, WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler
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

    _messaging_api: Optional[MessagingAPIWithEvents] = None
    
    @property
    def message_type(self) -> str:
        return "link_engine"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return LinkEngineRequest
    
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle engine linking."""
        try:
            print(message)
            req = LinkEngineRequest.model_validate(message)
            print(req)
        except Exception as e:
            logger.error(f"Error handling link engine request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling link engine request: {e}",
                    details=None
                )
            )
        
        try:
            session_id = req.data.session_id
            if not session_id:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.VALIDATION_ERROR,
                        message="session_id is required for link_engine",
                        details=None
                    )
                )
            engine_type = req.data.engine_type

            # Check if engine type is provided
            if not engine_type:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.INVALID_ENGINE_TYPE,
                        message="No engine type provided",
                        details=None
                    )
                )
            
            # Create engine based on type
            engine = None
            if engine_type in ENGINE_TYPES:
                engine = ENGINE_TYPES[engine_type](session_id=SessionID(session_id))
                # Initialize the engine (register tools, etc.) if it has an initialize method
                if hasattr(engine, 'initialize'):
                    await engine.initialize()
                if isinstance(engine, NotionCRUDEngineV3) and self._messaging_api:
                    engine.set_messaging_api(self._messaging_api)
            else:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.INVALID_ENGINE_TYPE,
                        message=f"Unknown engine type: {engine_type}",
                        details=None
                    )
                )

            
            # Register engine with engine service
            engine_service = EngineService()
            engine_id = engine_service.create_engine(engine)
            
            if engine_id:
                # Register engine to session
                engine_service.register_engine(SessionID(session_id), engine_id)
                logger.info(f"Linked engine {engine_id} for session {session_id}")
                
                return LinkEngineResponse(
                    type="link_engine_res",
                    message_id=req.message_id,
                    data=LinkEngineResponse.LinkEngineResponseData(
                        engine_id=str(engine_id),
                        session_id=str(session_id)
                    )
                )
            else:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.ENGINE_CREATION_FAILED,
                        message="Failed to create engine: maximum engines reached",
                        details=None
                    )
                )
            
        except Exception as e:
            logger.error(f"Error linking engine: {e}")
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.ENGINE_CREATION_FAILED,
                    message=f"Error linking engine: {str(e)}",
                    details=None
                )
            )


class UseEngineHandler(BaseHandler):
    """Handler for using registered engines."""

    _messaging_api: Optional[MessagingAPIWithEvents] = None
    
    @property
    def message_type(self) -> str:
        return "use_engine"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return UseEngineRequest
    
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle engine usage request."""
        try:
            req = UseEngineRequest.model_validate(message)
        except Exception as e:
            logger.error(f"Error handling use engine request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling use engine request: {e}",
                    details=None
                )
            )
        
        try:
            session_id = req.data.session_id
            if not session_id:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.VALIDATION_ERROR,
                        message="session_id is required for use_engine",
                        details=None
                    )
                )
            prompt : str = str(req.data.prompt)
            
            # Get registered engine for this session
            engine_service = EngineService()
            engine = engine_service.get_registered_engine(SessionID(session_id))
            
            if not engine:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.ENGINE_NOT_FOUND,
                        message="No engine registered for this session",
                        details=None
                    )
                )
            
            # Update engine interaction time
            engine_service.update_engine_last_interaction_at(engine.engine_id)
            
            # Use the engine based on type
            if isinstance(engine, FactProcessingEngine):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    type="use_engine_res",
                    message_id=req.message_id,
                    data=UseEngineResponse.UseEngineResponseData(
                        result=result,
                        session_id=str(session_id)
                    )
                )
                    
            elif isinstance(engine, NotionCRUDEngineV3):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    type="use_engine_res",
                    message_id=req.message_id,
                    data=UseEngineResponse.UseEngineResponseData(
                        result=result,
                        session_id=str(session_id)
                    )
                )
            else:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.ENGINE_NOT_FOUND,
                        message="Error in engine registration",
                        details=None
                    )
                )
                
        except Exception as e:
            logger.error(f"Error using engine: {e}")
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.ENGINE_CREATION_FAILED,
                    message=f"Error using engine: {str(e)}",
                    details=None
                )
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
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle engine types request."""  
        try:
            req = GetEngineTypesRequest.model_validate(message)
        except Exception as e:
            logger.error(f"Error handling get engine types request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling get engine types request: {e}",
                    details=None
                )
            )
        
        session_id = req.data.session_id

        try:
            if not session_id:
                return WSError(
                    type="error",
                    message_id=req.message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.VALIDATION_ERROR,
                        message="session_id is required for get_engine_types",
                        details=None
                    )
                )
            engine_types = list(ENGINE_TYPES.keys())
            return GetEngineTypesResponse(
                message_id=req.message_id,
                data=GetEngineTypesResponse.GetEngineTypesResponseData(
                    engine_types=engine_types,
                    session_id=str(session_id)
                )
            )
        except Exception as e:
            logger.error(f"Error getting engine types: {e}")
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.ENGINE_CREATION_FAILED,
                    message=f"Error getting engine types: {str(e)}",
                    details=None
                )
            )