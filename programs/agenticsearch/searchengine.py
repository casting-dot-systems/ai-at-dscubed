import asyncio
import os 
import json
import dotenv
import logging 

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logging.basicConfig(level=logging.INFO)

dotenv.load_dotenv()

@dataclass
class SearchEngineEvent(Event):

@dataclass
class SearchEngineCommand(Command):

@dataclass
class SearchEngineState(State):

class SearchEngine:
    def __init__(self):

    
    async def handle_command(self, command: SearchEngineCommand) -> SearchEngineEvent:

    async def execute():

    async def execute_tool(self, tool: str, args: Dict[str, Any]) -> Any:




