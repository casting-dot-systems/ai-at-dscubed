from dataclasses import dataclass
from typing import Any, Dict, List
from llmgine.messages import Command, CommandResult
from llmgine.messages import Event
from llmgine.llm.providers.openai_provider import OpenAIProvider
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.bus.bus import MessageBus
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm import SessionID
from program_types import DiscordChannelID

import asyncio
import uuid
import os
import dotenv

dotenv.load_dotenv()


@dataclass
class ScrumMasterCommand(Command):
    """Command to get the context of the scrum master"""

    prompt: str = ""


@dataclass
class ScrumMasterEngineStatusEvent(Event):
    """Event to get the status of the scrum master engine"""

    status: str = ""


@dataclass
class ScrumMasterConfirmEndConversationCommand(Command):
    """Command to confirm the end of the conversation"""

    prompt: str = ""
    channel_id: DiscordChannelID = DiscordChannelID("")


@dataclass
class ScrumMasterEngineToolResultEvent(Event):
    """Event to get the result of the tool call"""

    tool_name: str = ""
    result: str = ""


def request_end_conversation():
    """Call this function to request the end of the conversation"""
    return "end_conversation"


class ScrumMasterEngine:
    def __init__(
        self, system_prompt: str, session_id: SessionID, channel_id: DiscordChannelID
    ):
        """Get all the context"""
        self.bus = MessageBus()
        self.session_id = session_id
        self.channel_id = channel_id
        self.system_prompt = system_prompt
        self.engine_id = str(uuid.uuid4())
        self.model = OpenAIProvider(
            model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY")
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

    async def extract_conversation(self) -> List[Dict[str, Any]]:
        """Extract the conversation from the prompt"""
        conversation = await self.context_manager.retrieve()
        return conversation

    async def handle_command(self, command: ScrumMasterCommand) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        max_tool_calls = 99
        tool_call_count = 0
        self.context_manager.store_string(
            string=command.prompt,
            role="user",
        )
        try:
            while True:
                current_context = await self.context_manager.retrieve()
                tools = await self.tool_manager.get_tools()
                await self.bus.publish(
                    ScrumMasterEngineStatusEvent(
                        status="Calling LLM",
                        session_id=self.session_id,
                    )
                )
                response = await self.model.generate(
                    messages=current_context, tools=tools
                )

                # 5. Extract the first choice's message object
                # Important: Access the underlying OpenAI object structure
                response_message = response.raw.choices[0].message
                # 6. Add the *entire* assistant message object to history.
                # This is crucial for context if it contains tool_calls.
                await self.context_manager.store_assistant_message(response_message)

                # 7. Check for tool calls
                if not response_message.tool_calls:
                    # No tool calls, break the loop and return the content
                    final_content = response_message.content or ""
                    await self.bus.publish(
                        ScrumMasterEngineStatusEvent(
                            status="finished",
                            session_id=self.session_id,
                        )
                    )
                    return CommandResult(success=True, result=final_content)

                # 8. Process tool call
                for tool_call in response_message.tool_calls:
                    await self.bus.publish(
                        ScrumMasterEngineStatusEvent(
                            status="Executing tool call",
                            session_id=self.session_id,
                        )
                    )
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                    result = await self.bus.execute(
                        ScrumMasterConfirmEndConversationCommand(
                            prompt="Stella would like to end the converstion.",
                            channel_id=self.channel_id,
                            session_id=self.session_id,
                        )
                    )
                    if result.result:
                        self.context_manager.store_tool_call_result(
                            tool_call_id=tool_call_obj.id,
                            name=tool_call_obj.name,
                            content="The user has confirmed to end the conversation.",
                        )
                        await self.bus.publish(
                            ScrumMasterEngineToolResultEvent(
                                tool_name=tool_call_obj.name,
                                result="The user has confirmed to end the conversation.",
                            )
                        )
                    else:
                        self.context_manager.store_tool_call_result(
                            tool_call_id=tool_call_obj.id,
                            name=tool_call_obj.name,
                            content="The user would like to continue the conversation.",
                        )
                        await self.bus.publish(
                            ScrumMasterEngineToolResultEvent(
                                tool_name=tool_call_obj.name,
                                result="The user would like to continue the conversation.",
                            )
                        )
        except Exception as e:
            print(e)
            await self.bus.publish(
                ScrumMasterEngineStatusEvent(
                    status="finished",
                    session_id=self.session_id,
                )
            )
            return CommandResult(
                success=False,
                result="Sorry, I crashed ): Give us a moment we will get back to you soon.",
            )


async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import (
        EngineResultComponent,
        ToolComponentShort,
        YesNoPrompt,
    )

    from tools.general.functions import store_fact
    from tools.gmail.gmail_client import read_emails, reply_to_email, send_email

    app = ApplicationBootstrap(ApplicationConfig(enable_console_handler=False))
    await app.bootstrap()
    cli = EngineCLI("test")
    engine = ScrumMasterEngine(
        system_prompt=f"""You are a scrum master. You are responsible for managing the scrum process. After the user has finished their checkup, if you believe the user will want to end the conversation, 
        you will call the request_end_conversation tool.
        """,
        session_id="test",
    )
    await engine.tool_manager.register_tool(request_end_conversation)
    cli.register_engine(engine)
    cli.register_engine_command(ScrumMasterCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(ScrumMasterEngineStatusEvent)
    cli.register_component_event(ScrumMasterEngineToolResultEvent, ToolComponentShort)
    cli.register_prompt_command(ScrumMasterConfirmEndConversationCommand, YesNoPrompt)
    await cli.main()


if __name__ == "__main__":
    asyncio.run(main())
