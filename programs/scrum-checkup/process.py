import asyncio
from dataclasses import dataclass
from uuid import uuid4
from llmgine.messages import Event
from llmgine.bus.bus import MessageBus
from bot import main_darcy_bot
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


@dataclass
class CheckUpEvent(Event):
    """Event to check up on the user"""

    user_discord_id: str = ""


# async def check_up_event_handler(event: CheckUpEvent):
#     """Handler for the check up event"""
#     print(f"Checking up on user {event.user_id}")
#     bus = MessageBus()
#     session_id = uuid4()
#     context = await get_context(event.user_id)
#     channel = await get_channel(event.user_id)
#     main_darcy_bot.register_channel(session_id, channel)
#     # create engine
#     engine = ScrumMasterEngine(context, session_id)
#     response = await engine.handle_command(ScrumMasterCommand(prompt=context))
#     await send_message(response.result, channel)

#     # generate first message
#     # send first message in channel
#     # wait for response


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
    context = await get_context("241085495398891521")
    print(context)
    tasks = await fetch_user_tasks("f746733c-66cc-4cbc-b553-c5d3f03ed240")
    print(tasks)


if __name__ == "__main__":
    asyncio.run(main())
