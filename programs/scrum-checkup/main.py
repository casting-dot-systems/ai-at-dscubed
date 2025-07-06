"""
Main entry point for the Scrum Master Bot.
This file handles the startup and avoids circular imports.
"""

import asyncio
from llmgine.bus.bus import MessageBus
from scrum_checkup_post_process import check_up_finished_event_handler
from scrum_checkup_types import CheckUpEvent, CheckUpFinishedEvent
from bot import ScrumMasterBot


async def main() -> None:
    """Main entry point for the bot."""
    from scrum_checkup_pre_process import check_up_event_handler

    bus: MessageBus = MessageBus()
    with open("prompts/scrum_process.md", "r") as f:
        prompt = f.read()
    await bus.start()
    bus.register_event_handler(CheckUpEvent, check_up_event_handler)
    bus.register_event_handler(CheckUpFinishedEvent, check_up_finished_event_handler)

    await ScrumMasterBot.get_instance().start()


if __name__ == "__main__":
    asyncio.run(main())
