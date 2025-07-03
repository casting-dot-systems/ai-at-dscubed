import asyncio
from dataclasses import dataclass
from uuid import uuid4
from llmgine.messages import Event
from llmgine.bus.bus import MessageBus
from bot import main_darcy_bot
from scrum_engine import ScrumMasterCommand, ScrumMasterEngine


@dataclass
class CheckUpEvent(Event):
    """Event to check up on the user"""

    user_id: str = ""


async def check_up_event_handler(event: CheckUpEvent):
    """Handler for the check up event"""
    print(f"Checking up on user {event.user_id}")
    bus = MessageBus()
    session_id = uuid4()
    context = await get_context(event.user_id)
    channel = await get_channel(event.user_id)
    main_darcy_bot.register_channel(session_id, channel)
    # create engine
    engine = ScrumMasterEngine(context, session_id)
    response = await engine.handle_command(ScrumMasterCommand(prompt=context))
    await send_message(response.result, channel)

    # generate first message
    # send first message in channel
    # wait for response


async def send_message(message: str, channel: str):
    """Send a message to the channel"""
    await main_darcy_bot.bot.get_channel(channel).send(message)


async def get_context(user_id: str) -> str:
    return None


async def get_channel(user_id: str) -> str:
    return None
