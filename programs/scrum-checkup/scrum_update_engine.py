from dataclasses import dataclass
from typing import Any, Optional
from llmgine.messages import Command, CommandResult
from llmgine.messages import Event
from llmgine.llm.providers.openai_provider import OpenAIProvider
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.bus.bus import MessageBus
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm import SessionID
from llmgine.llm.providers.response import LLMResponse

import asyncio
import uuid
import os
import dotenv

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

def get_next_scrum_time():
    """Call this function to get the next scrum time"""
    return "10:00:00"

def get_current_date():
    """Call this function to get the current date"""
    return "2025-07-03"

def update_database(current_plan_structured: str, current_plan_unstructured: str, next_scrum_time: str):
    """Call this function to update the database
    
    Args:
        current_plan_structured: The structured plan of the user, written in the format specified in the prompt
        current_plan_unstructured: The unstructured plan of the user, written in mostly user's words, include task names and ETA
        next_scrum_time: The time of the next scrum, in the format of YYYY-MM-DD HH:MM:SS
    """

    print(f"Current plan structured: {current_plan_structured}")
    print(f"Current plan unstructured: {current_plan_unstructured}")
    print(f"Next scrum time: {next_scrum_time}")
    return "database updated successfully"

class ScrumUpdateEngine:
    def __init__(self, system_prompt: str, session_id: str):
        """Get all the context"""
        self.bus = MessageBus()
        self.session_id = SessionID(session_id)
        self.engine_id = str(uuid.uuid4())
        self.system_prompt = system_prompt
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
                response : LLMResponse = await self.model.generate(
                    messages=current_context, tools=tools
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
                    
                    result : Optional[Any] = await self.tool_manager.execute_tool_call(tool_call_obj)

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

async def useScrumUpdateEngine(session_id: str, discord_id: str):
    engine = ScrumUpdateEngine(
        system_prompt=f"""You are a scrum master. You are responsible for managing the post daily scrum process. 
        The user has provided their plan on what they would do with their current tasks. You should summarize their plan and
        update the database. Also, schedule the next daily scrum based on the user's plan.

        If the user does not mention about the next scrum time, you should fetch the next scrum time from the database using the get_next_scrum_time tool for the time, and the
        next scrum date will be tomorrow.

        Here is a structured plan example for updating the database:
        
        Date: YYYY-MM-DD
            Will complete Task XXXXX by YYYY-MM-DD
            Will complete Task XXXXX by YYYY-MM-DD
            ...

        ie.
        Date: 2025-07-03
            Will complete Task "Create Engine" by 2025-07-04
            Will complete Task "Research MCP" by 2025-07-05
            Will complete Task "Brainstorm schema" by 2025-07-10

        """,
        session_id=session_id,
    )
    await engine.tool_manager.register_tool(update_database)
    await engine.tool_manager.register_tool(get_next_scrum_time)
    await engine.tool_manager.register_tool(get_current_date)
    await engine.handle_command(ScrumUpdateCommand(prompt=f"""You're current tasks are:
        - Research MCP
        - Complete tool chat bot
        - Design DB schema

        I will try and get the first two finished by tmr. The third task will prob take a bit longer, i'm not sure at this stage."""))


async def main(useEngine: bool = False):
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import (
        EngineResultComponent,
        ToolComponentShort,
    )

    engine = ScrumUpdateEngine(
        system_prompt=f"""You are a scrum master. You are responsible for managing the post daily scrum process. 
        The user has provided their plan on what they would do with their current tasks. You should summarize their plan and
        update the database. Also, schedule the next daily scrum based on the user's plan.

        If the user does not mention about the next scrum time, you should fetch the next scrum time from the database using the get_next_scrum_time tool for the time, and the
        next scrum date will be tomorrow.

        Here is a structured plan example for updating the database:
        
        Date: YYYY-MM-DD
            Will complete Task XXXXX by YYYY-MM-DD
            Will complete Task XXXXX by YYYY-MM-DD
            ...

        ie.
        Date: 2025-07-03
            Will complete Task "Create Engine" by 2025-07-04
            Will complete Task "Research MCP" by 2025-07-05
            Will complete Task "Brainstorm schema" by 2025-07-10

        """,
        session_id="test",
    )
    await engine.tool_manager.register_tool(update_database)
    await engine.tool_manager.register_tool(get_next_scrum_time)
    await engine.tool_manager.register_tool(get_current_date)


    if useEngine:
        await engine.handle_command(ScrumUpdateCommand(prompt=f"""You're current tasks are:
            - Research MCP
            - Complete tool chat bot
            - Design DB schema

            I will try and get the first two finished by tmr. The third task will prob take a bit longer, i'm not sure at this stage."""))
    else:
        app = ApplicationBootstrap(ApplicationConfig(enable_console_handler=False))
        await app.bootstrap()
        cli = EngineCLI(SessionID("test"))
        cli.register_engine(engine)
        cli.register_engine_command(ScrumUpdateCommand, engine.handle_command)
        cli.register_engine_result_component(EngineResultComponent)
        cli.register_loading_event(ScrumUpdateEngineStatusEvent)
        cli.register_component_event(ScrumUpdateEngineToolResultEvent, ToolComponentShort)
        await cli.main()

if __name__ == "__main__":
    asyncio.run(main(useEngine=True))
