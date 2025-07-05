from typing import NewType, Dict, Any


DiscordChannelID = NewType("DiscordChannelID", str)
SessionContext = NewType("SessionContext", Dict[str, Any])
