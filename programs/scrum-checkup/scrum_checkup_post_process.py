import asyncio
from dataclasses import dataclass
from uuid import uuid4
from llmgine.messages import Event
from llmgine.bus.bus import MessageBus
from scrum_checkup_types import CheckUpFinishedEvent, DiscordChannelID, CheckUpEvent
from scrum_checkup_engine import ScrumMasterCommand, ScrumMasterEngine
from scrum_update_engine import useScrumUpdateEngine
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


async def check_up_finished_event_handler(event: CheckUpFinishedEvent):
    context = event.checkup_context
    await useScrumUpdateEngine(context)
    set_committee_personal_checkup(
        context.discord_id, str(context.conversation), datetime.now()
    )
