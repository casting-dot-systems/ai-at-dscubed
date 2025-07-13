import uuid
from typing import NewType, Dict, Any
from enum import Enum

from discord.ext import commands
from llmgine.llm import SessionID

from team_engine import TeamAssignmentEngine, TeamAssignmentCommand
from groupfunctions import GroupFunctions
from llmgine.bus.bus import MessageBus

DiscordChannelID = NewType("DiscordChannelID", str)
SessionContext = NewType("SessionContext", Dict[str, Any])


class SessionManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_register: dict[DiscordChannelID, tuple[SessionID, TeamAssignmentEngine]] = {}

    async def create_session(
            self, 
            channel_id: DiscordChannelID, 
            engine: TeamAssignmentEngine,
    ) -> SessionID:
        
        session_id = SessionID(str(uuid.uuid4()))

        self.channel_register[str(channel_id)] = (
            session_id,
            engine, 
            SessionContext({}),
        )

        MessageBus().register_command_handler(
            TeamAssignmentCommand,
            self.handle_command,
            session_id=session_id,
        )

        init_message = await engine.handle_command(
            TeamAssignmentCommand(
                prompt="Start the process",
                session_id=session_id,
            )
        )
        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            raise ValueError(f"Channel {int(channel_id)} not found")
        await channel.send(
            f"# Team Assignment Session Started"
        )  

        return session_id
    
    async def end_session(
           self, 
           channel_id: DiscordChannelID,
    ) -> None:
        print(f"Ending session for channel {channel_id}")
        self.channel_register.pop(str(channel_id))
    
class SessionStatus(Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
