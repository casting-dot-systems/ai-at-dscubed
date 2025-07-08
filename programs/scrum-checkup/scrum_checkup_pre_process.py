import asyncio
from dataclasses import dataclass
from uuid import uuid4
from llmgine.messages import Event
from llmgine.bus.bus import MessageBus
from custom_types.notion import NotionUserID
from scrum_checkup_types import CheckUpEventContext, DiscordChannelID, CheckUpEvent
from scrum_checkup_engine import ScrumMasterCommand, ScrumMasterEngine
from custom_tools.database.database import (
    get_committee_member_by_discord_id,
    get_committee_member_by_notion_id,
    get_latest_personal_checkup,
    get_checkups_for_discord_id,
    set_committee_personal_checkup,
    set_personal_description,
)
from custom_tools.notion.fetch_active_user_tasks import get_task_and_project_info
from llmgine.prompts.prompts import get_prompt, Prompt
from llmgine.llm import SessionID
from datetime import datetime
from bot import ScrumMasterBot
from custom_types.discord import DiscordUserID
from llmgine.llm import LLMConversation


async def check_up_event_handler(event: CheckUpEvent):
    """Handler for the check up event"""

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


async def main():
    # context = await get_context("241085495398891521")
    # print(context)
    # tasks = await fetch_user_tasks("f746733c-66cc-4cbc-b553-c5d3f03ed240")
    # print(tasks)
    print(
        await check_up_event_handler(CheckUpEvent(user_discord_id="241085495398891521"))
    )


if __name__ == "__main__":
    asyncio.run(main())
