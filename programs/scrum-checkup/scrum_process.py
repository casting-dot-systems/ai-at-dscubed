import asyncio
from dataclasses import dataclass
from uuid import uuid4
from llmgine.messages import Event
from llmgine.bus.bus import MessageBus
from program_types import DiscordChannelID, CheckUpEvent
from scrum_engine import ScrumMasterCommand, ScrumMasterEngine
from tools.database.database import (
    get_committee_member_by_discord_id,
    get_committee_member_by_notion_id,
    get_latest_personal_checkup,
    get_checkups_for_discord_id,
    set_committee_personal_checkup,
    set_personal_description,
)
from tools.notion.fetch_active_user_tasks import get_task_and_project_info
from llmgine.prompts.prompts import get_prompt, Prompt
from datetime import datetime
from bot import ScrumMasterBot


async def check_up_event_handler(event: CheckUpEvent):
    """Handler for the check up event"""

    print(f"Checking up on user {event.user_discord_id}")
    bus = MessageBus()
    session_id = str(uuid4())
    context = await get_context(event.user_discord_id)
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
    print(
        f"\n\nScrumMasterBot instance in handler: {ScrumMasterBot.get_instance()}\n\n"
    )
    await ScrumMasterBot.get_instance().create_session(
        session_id,
        DiscordChannelID(user_row["discord_dm_channel_id"]),
        ScrumMasterEngine(
            prompt, session_id, DiscordChannelID(user_row["discord_dm_channel_id"])
        ),
        event.user_discord_id,
    )
    # instance 1 0x75fd60006120
    # instance 3 0x75FD60006120
    # instance 2 0x75FD618D9160
    # generate first message
    # send first message in channel
    # wait for response


async def get_context(discord_id: str) -> str:
    user = get_committee_member_by_discord_id(discord_id)
    if user is None:
        raise ValueError(f"User with discord_id {discord_id} not found")
    notion_id = user["notion_id"]
    if notion_id is None:
        raise ValueError(f"User with discord_id {discord_id} has no notion_id")
    return user


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
