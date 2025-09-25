"""
FastAPI backend for darcy_backend using llmgine extensibility framework.

This module extends the llmgine API to provide WebSocket endpoints for:
- Registering fact processing engines
- Registering Notion CRUD engines  
- Using registered engines with commands

Based on llmgine/src/api/examples/custom_engine_example.py pattern.
"""

import uvicorn
import logging

from llmgineAPI.core.extensibility import (
    ExtensibleAPIFactory, 
    EngineConfiguration
)

from handlers import LinkEngineHandler, UseEngineHandler, GetEngineTypesHandler

logger = logging.getLogger(__name__)


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
    
    # Get messaging API and store it for handlers to access (after app creation)
    messaging_api = darcy_api.get_messaging_api()
    
    # Store messaging API in handler classes
    LinkEngineHandler._messaging_api = messaging_api
    UseEngineHandler._messaging_api = messaging_api
    
    # Also store in app state for other uses
    app.state.messaging_api = messaging_api
    
    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=8000)