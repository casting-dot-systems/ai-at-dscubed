from .fact_processing_engine import FactProcessingEngine
from .notion_crud_engine_v3 import NotionCRUDEngineV3

__all__ = ["FactProcessingEngine", "NotionCRUDEngineV3"]

ENGINE_TYPES = {
    "fact_processing": FactProcessingEngine,
    "notion_crud": NotionCRUDEngineV3
}
