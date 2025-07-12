"""
This module contains the types for the scrum checkup process.
Includes the dataclasses for the scrum checkup pre event and the scrum checkup post event,
as well as the handlers for those events.

Here is the flow of the process:

-- pre event --
1. The user triggers the checkup event by typing `/scrum-checkup` in the discord channel OR automatically triggered by a scheduled event.
2. The user's context (personal description, tasks, projects, etc.) is fetched.

-- checkup event --
3. The LLM is used to generate a checkup request, asking for updates on the user's tasks and projects.
4. The user's response is sent to the LLM.

-- post event --
5. The checkup finished event is triggered.
6. The conversation context is used to update the notion task progress.
7. The conversation context is used to update the database.
8. The next personal checkup is scheduled.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, override
from uuid import uuid4
import asyncio

from llmgine.messages import ScheduledEvent, Event, register_scheduled_event_class
from llmgine.llm import SessionID, LLMConversation
from llmgine.prompts.prompts import get_prompt

from custom_types.discord import DiscordChannelID, DiscordUserID
from custom_types.notion import NotionUserID
from custom_tools.brain.postgres.database import (
    get_committee_member_by_discord_id,
    get_checkups_for_discord_id,
    set_committee_personal_checkup
)
from custom_tools.brain.notion.fetch_active_user_tasks import get_task_and_project_info



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

    @override
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "session_id": self.session_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "user_discord_id": self.user_discord_id
        }
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> "CheckUpEvent":
        """
        Create a CheckUpEvent from a dictionary.
        """
        if "scheduled_time" in event_dict:
            event_dict["scheduled_time"] = datetime.fromisoformat(event_dict["scheduled_time"])
        return cls(**event_dict)
register_scheduled_event_class(CheckUpEvent)

@dataclass
class CheckUpFinishedEvent(Event):
    """Event to check up on the user"""

    checkup_context: CheckUpEventContext = field(default_factory=CheckUpEventContext)

async def check_up_event_handler(event: CheckUpEvent):
    """Handler for the check up event"""

    from bot import ScrumMasterBot

    print(f"Checking up on user {event.user_discord_id}")

    user_row = get_committee_member_by_discord_id(event.user_discord_id)

    if user_row is None:
        raise ValueError(
            f"User with discord_id {event.user_discord_id} not found in database"
        )

    if user_row.get("discord_dm_channel_id") is None:
        raise ValueError(
            f"User with discord_id {event.user_discord_id} has no discord_dm_channel_id set"
        )

    user_context = get_checkups_for_discord_id(event.user_discord_id)

    tasks = await fetch_user_tasks(user_row["notion_id"])

    additional_info = f"The datetime is {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    prompt = get_prompt("prompts/scrum_process.md")

    prompt = prompt.format(
        person_description=user_context["personal_description"],
        current_tasks=tasks,
        last_checkup=user_context["last_checkup"],
        additional_info=additional_info,
    )

    checkup_context = CheckUpEventContext(
        session_id=SessionID(str(uuid4())),
        discord_id=DiscordUserID(str(event.user_discord_id)),
        notion_id=NotionUserID(str(user_row["notion_id"])),
        checkup_channel_id=DiscordChannelID(str(user_row["discord_dm_channel_id"])),
        personal_description=user_context["personal_description"],
        system_prompt=prompt,
        conversation=LLMConversation([]),
    )

    await ScrumMasterBot.get_instance().create_session(checkup_context)


async def fetch_user_tasks(notion_id: str) -> str:
    tasks, projects = get_task_and_project_info(notion_id)
    return f"User tasks: {tasks}\nUser projects: {projects}"


async def check_up_finished_event_handler(event: CheckUpFinishedEvent):
    """Handler for the check up finished event"""
    from scrum_update_engine import useScrumUpdateEngine

    context = event.checkup_context
    
    # Set next personal checkup and update notion task progress
    await useScrumUpdateEngine(context)

    # Update the personal checkup in the database
    set_committee_personal_checkup(
        context.discord_id, str(context.conversation), datetime.now()
    )


async def main():
    # context = await get_context("241085495398891521")
    # print(context)
    # tasks = await fetch_user_tasks("f746733c-66cc-4cbc-b553-c5d3f03ed240")
    # print(tasks)
    print(
        await check_up_event_handler(CheckUpEvent(user_discord_id="774065995508744232"))
    )


if __name__ == "__main__":
    asyncio.run(main())
