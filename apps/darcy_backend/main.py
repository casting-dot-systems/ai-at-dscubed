"""
FastAPI backend for darcy_backend using llmgine extensibility framework.

This module extends the llmgine API to provide WebSocket endpoints for:
- Registering fact processing engines
- Registering Notion CRUD engines  
- Using registered engines with commands

Based on llmgine/src/api/examples/custom_engine_example.py pattern.
"""

from typing import Optional, List
from fastapi import WebSocket
import uvicorn
import logging

from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.core.extensibility import (
    CustomMessageMixin, 
    ExtensibleAPIFactory, 
    EngineConfiguration
)
from llmgine.llm import SessionID
from llmgineAPI.services.engine_service import EngineService

# Import our engines
from engines.fact_processing_engine import FactProcessingEngine
from engines.notion_crud_engine_v3 import NotionCRUDEngineV3
from engines import ENGINE_TYPES

logger = logging.getLogger(__name__)

# ================================ CUSTOM MESSAGE TYPES ================================

class GetEngineTypesRequest(WSMessage, CustomMessageMixin):
    """Custom message for getting engine types."""

    def __init__(self):
        super().__init__(
            type="get_engine_types",
            data={}
        )

class GetEngineTypesResponse(WSResponse):
    """Custom response for getting engine types."""

    def __init__(self, engine_types: List[str]):
        super().__init__(
            type="get_engine_types_res",
            data={"engine_types": engine_types}
        )

class LinkEngineRequest(WSMessage, CustomMessageMixin):
    """Custom message for linking an engine."""
    
    def __init__(self, engine_type: str):
        super().__init__(
            type="link_engine",
            data={
                "engine_type": engine_type
            }
        )

class LinkEngineResponse(WSResponse):
    """Custom response for linking an engine."""
    
    def __init__(self, engine_id: str, success: bool, message: str):
        super().__init__(
            type="link_engine_res",
            data={
                "engine_id": engine_id,
                "success": success,
                "message": message
            }
        )


class UseEngineRequest(WSMessage, CustomMessageMixin):
    """Custom message for using a registered engine."""
    
    def __init__(self, prompt: str):
        super().__init__(
            type="use_engine",
            data={"prompt": prompt}
        )


class UseEngineResponse(WSResponse):
    """Custom response for engine usage."""
    
    def __init__(self, result: str, success: bool, message: Optional[str] = None):
        super().__init__(
            type="use_engine_res",
            data={
                "result": result,
                "success": success,
                "message": message
            }
        )

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
                return LinkEngineResponse(
                    engine_id="",
                    success=False,
                    message="No engine type provided"
                )
            
            # Create engine based on type
            engine = None
            if engine_type in ENGINE_TYPES:
                engine = ENGINE_TYPES[engine_type](session_id=session_id)
                # Initialize the engine (register tools, etc.) if it has an initialize method
                if hasattr(engine, 'initialize'):
                    await engine.initialize()
            else:
                return LinkEngineResponse(
                    engine_id="",
                    success=False,
                    message=f"Unknown engine type: {engine_type}"
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
                    success=True,
                    message=f"Engine linked successfully"
                )
            else:
                return LinkEngineResponse(
                    engine_id="",
                    success=False,
                    message="Failed to create engine: maximum engines reached"
                )
                
        except Exception as e:
            logger.error(f"Error linking engine: {e}")
            return LinkEngineResponse(
                engine_id="",
                success=False,
                message=f"Error linking engine: {str(e)}"
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
                return UseEngineResponse(
                    result="",
                    success=False,
                    message="No engine registered for this session"
                )
            
            # Update engine interaction time
            engine_service.update_engine_last_interaction_at(engine.engine_id)
            
            # Use the engine based on type
            if isinstance(engine, FactProcessingEngine):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    result=result,
                    success=True,
                    message="Fact processing completed"
                )
                    
            elif isinstance(engine, NotionCRUDEngineV3):
                result = await engine.execute(prompt)
                return UseEngineResponse(
                    result=result,
                    success=True,
                    message="Notion CRUD operation completed"
                )
            else:
                return UseEngineResponse(
                    result="",
                    success=False,
                    message="Error in engine registration"
                )
                
        except Exception as e:
            logger.error(f"Error using engine: {e}")
            return UseEngineResponse(
                result="",
                success=False,
                message=f"Error using engine: {str(e)}"
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
            return GetEngineTypesResponse(engine_types)
        except Exception as e:
            logger.error(f"Error getting engine types: {e}")

# ================================ FACTORY FUNCTION ================================

def create_darcy_api():
    """
    Create a customized API instance for darcy engines.
    
    This follows the pattern from custom_engine_example.py
    """
    
    # Create configuration
    config = EngineConfiguration(
        engine_name="DarcyEngine",
        custom_settings={
            "supported_engines": ["fact_processing", "notion_crud"],
            "max_engines_per_session": 2,
            "enable_engine_switching": True
        }
    )
    
    # Create API factory
    api_factory = ExtensibleAPIFactory(config)
    
    # Register custom handlers
    api_factory.register_custom_handler("link_engine", LinkEngineHandler)
    api_factory.register_custom_handler("use_engine", UseEngineHandler)
    api_factory.register_custom_handler("get_engine_types", GetEngineTypesHandler)
    
    # Get API metadata
    metadata = api_factory.get_api_metadata()
    logger.info(f"Created API for {metadata['engine_name']}")
    logger.info(f"Custom message types: {metadata['custom_message_types']}")
    
    return api_factory

# ================================ MAIN EXECUTION ================================

if __name__ == "__main__":
    # Create darcy API
    darcy_api = create_darcy_api()
    
    # Create app using llmgine main
    from llmgineAPI.main import create_app
    app = create_app(api_factory=darcy_api)
    
    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=8000)