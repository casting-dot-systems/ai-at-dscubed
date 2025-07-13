from llmgine.bus.bus import MessageBus
from bot import TeamAssignmentBot

import asyncio

async def main() -> None:
    bus: MessageBus = MessageBus()
    await bus.start()
    await TeamAssignmentBot.get_instance().start()

if __name__ == "__main__":
    asyncio.run(main())
