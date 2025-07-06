from dataclasses import dataclass, field
from llmgine.messages.events import ScheduledEvent
from llmgine.messages import Event
from llmgine.llm import SessionID, LLMConversation
from custom_types.discord import DiscordChannelID, DiscordUserID
from custom_types.notion import NotionUserID


@dataclass
class CheckUpEventContext:
    """A dataclass that can be passed around to various functions"""

    session_id: SessionID = SessionID("")
    discord_id: DiscordUserID = DiscordUserID("")
    notion_id: NotionUserID = NotionUserID("")
    checkup_channel_id: DiscordChannelID = DiscordChannelID("")
    personal_description: str = ""
    system_prompt: str = ""
    conversation: LLMConversation = field(default_factory=lambda: LLMConversation([]))
    tasks_context: str = ""  # temp
    # tasks: List[Dict[str, Any]] = []
    # projects: List[Dict[str, Any]] = []


@dataclass
class CheckUpEvent(ScheduledEvent):
    """Event to check up on the user"""

    user_discord_id: str = ""


@dataclass
class CheckUpFinishedEvent(Event):
    """Event to check up on the user"""

    checkup_context: CheckUpEventContext = field(default_factory=CheckUpEventContext)
