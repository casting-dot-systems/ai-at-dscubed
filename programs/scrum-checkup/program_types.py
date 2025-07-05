from typing import NewType, Dict, Any
from dataclasses import dataclass
from llmgine.messages import Event

DiscordChannelID = NewType("DiscordChannelID", str)
SessionContext = NewType("SessionContext", Dict[str, Any])


@dataclass
class CheckUpEvent(Event):
    """Event to check up on the user"""

    user_discord_id: str = ""
