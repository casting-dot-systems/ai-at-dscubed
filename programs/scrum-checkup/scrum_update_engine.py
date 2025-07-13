import asyncio
import uuid
import os
import dotenv
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from llmgine.messages import Command, CommandResult
from llmgine.messages import Event
from llmgine.llm import LLMConversation
from llmgine.llm.providers.openai_provider import OpenAIProvider
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.bus.bus import MessageBus
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm import SessionID
from llmgine.llm.providers.response import LLMResponse

from custom_tools.brain.postgres.postgres import get_committee_member_by_discord_id
from custom_types.discord import DiscordChannelID, DiscordUserID
from custom_types.notion import NotionUserID
from custom_tools.brain.notion.notion_functions import update_task, update_task_progress
from scrum_checkup_types import CheckUpEventContext



dotenv.load_dotenv()


@dataclass
class ScrumUpdateCommand(Command):
    """Command to get the context of the scrum master"""

    prompt: str = ""


@dataclass
class ScrumUpdateEngineStatusEvent(Event):
    """Event to get the status of the scrum master engine"""

    status: str = ""


@dataclass
class ScrumUpdateEngineToolResultEvent(Event):
    """Event to get the result of the tool call"""

    tool_name: str = ""
    result: str = ""

class ScrumUpdateEngine:
    def __init__(self, system_prompt: str, session_id: str, user_discord_id: str):
        """Get all the context"""
        self.bus = MessageBus()
        self.session_id = SessionID(session_id)
        self.engine_id = str(uuid.uuid4())
        self.system_prompt = system_prompt
        self.user_discord_id = user_discord_id
        self.model = OpenAIProvider(
            model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY") or ""
        )
        self.context_manager: SimpleChatHistory = SimpleChatHistory(
            engine_id=self.engine_id, session_id=self.session_id
        )
        self.tool_manager: ToolManager = ToolManager(
            engine_id=self.engine_id,
            session_id=self.session_id,
            llm_model_name="openai",
        )
        self.context_manager.set_system_prompt(self.system_prompt)

    async def handle_command(self, command: ScrumUpdateCommand) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """

        self.context_manager.store_string(
            string=command.prompt,
            role="user",
        )
        try:
            while True:
                current_context = await self.context_manager.retrieve()
                tools = await self.tool_manager.get_tools()
                await self.bus.publish(
                    ScrumUpdateEngineStatusEvent(
                        status="Calling LLM",
                        session_id=self.session_id,
                    )
                )
                response: LLMResponse = await self.model.generate( # type: ignore
                    messages=current_context, tools=tools # type: ignore
                )

                response_message = response.raw.choices[0].message
                await self.context_manager.store_assistant_message(response_message)

                if not response_message.tool_calls:
                    # No tool calls, break the loop and return the content
                    final_content = response_message.content or ""
                    await self.bus.publish(
                        ScrumUpdateEngineStatusEvent(
                            status="finished",
                            session_id=self.session_id,
                        )
                    )
                    return CommandResult(success=True, result=final_content)

                for tool_call in response_message.tool_calls:
                    await self.bus.publish(
                        ScrumUpdateEngineStatusEvent(
                            status="Executing tool call",
                            session_id=self.session_id,
                        )
                    )
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )

                    result: Optional[Any] = await self.tool_manager.execute_tool_call(
                        tool_call_obj
                    )

                    self.context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=str(result),
                    )
                    await self.bus.publish(
                        ScrumUpdateEngineToolResultEvent(
                            tool_name=tool_call_obj.name,
                            result=str(result),
                        )
                    )

        except Exception as e:
            print(e)
            await self.bus.publish(
                ScrumUpdateEngineStatusEvent(
                    status="finished",
                    session_id=self.session_id,
                )
            )
            return CommandResult(
                success=False,
                result="Sorry, I crashed ): Give us a moment we will get back to you soon.",
            )

    async def schedule_next_scrum(self, scheduled_datetime: str):
        """Schedule the next scrum time based on the conversation.

        Args:
            scheduled_datetime: The datetime when the next scrum should be scheduled in ISO format (YYYY-MM-DDTHH:MM:SS)
            user_discord_id: The Discord user ID to schedule the scrum for
        """
        from datetime import datetime
        from scrum_checkup_types import CheckUpEvent

        try:
            scheduled_time = datetime.fromisoformat(scheduled_datetime)
            await MessageBus().publish(
                CheckUpEvent(
                    user_discord_id=self.user_discord_id, scheduled_time=scheduled_time
                )
            )
            print(f"Successfully scheduled next scrum for {scheduled_datetime}")
            return f"Successfully scheduled next scrum for {scheduled_datetime}"
        except ValueError as e:
            return f"Error parsing datetime: {e}. Please use ISO format (YYYY-MM-DDTHH:MM:SS)"


async def useScrumUpdateEngine(checkup_context: CheckUpEventContext):
    user_row = get_committee_member_by_discord_id(checkup_context.discord_id)
    if user_row is None:
        raise ValueError(f"User with discord_id {checkup_context.discord_id} not found in database")
    user_name = user_row["name"]

    engine = ScrumUpdateEngine(
        system_prompt=f"""You will be given a conversation between {user_name} and a scrum master. You will then schedule the next scrum time based on the conversation. The current datetime is {datetime.now()}.
        For tasks mentioned in the conversation, you will need to update the task status when necessary. ie. if the user says "I have finished task 1", you will need to update the task status to "Done".
        For every task mentioned in the conversation, you will need to update the task progress using the update_task_progress tool.
        """,
        session_id=SessionID(str(uuid.uuid4())),
        user_discord_id=checkup_context.discord_id,
    )
    await engine.tool_manager.register_tool(engine.schedule_next_scrum)
    await engine.tool_manager.register_tool(update_task)
    await engine.tool_manager.register_tool(update_task_progress)
    await engine.handle_command(
        ScrumUpdateCommand(prompt=str(checkup_context.conversation))
    )


async def main():
    await MessageBus().start()
    checkup_context = CheckUpEventContext(
        session_id=SessionID(str(uuid.uuid4())),
        discord_id=DiscordUserID("774065995508744232"),
        notion_id=NotionUserID("1bbd872b-594c-8123-a9c8-0002e6ee833b"),
        checkup_channel_id=DiscordChannelID("1389101580363632692"),
        personal_description="",
        system_prompt="",
        conversation=LLMConversation(
            [{"role": "user", "content": "Next CHeckup is in 10 minutes"}]
        ),
    )
    await useScrumUpdateEngine(checkup_context)

if __name__ == "__main__":
    asyncio.run(main())
