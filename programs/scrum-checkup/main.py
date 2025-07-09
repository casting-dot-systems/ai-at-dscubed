"""
Main entry point for the Scrum Master Bot.
This file handles the startup and avoids circular imports.
"""

import asyncio

from llmgine.bus.bus import MessageBus

from bot import ScrumMasterBot
from scrum_checkup_types import CheckUpEvent, CheckUpFinishedEvent, check_up_event_handler, check_up_finished_event_handler


async def main() -> None:
    """Main entry point for the bot."""

    bus: MessageBus = MessageBus()

    await bus.start()
    bus.register_event_handler(CheckUpEvent, check_up_event_handler) # type: ignore
    bus.register_event_handler(CheckUpFinishedEvent, check_up_finished_event_handler) # type: ignore

    await ScrumMasterBot.get_instance().start()


if __name__ == "__main__":
    asyncio.run(main())
