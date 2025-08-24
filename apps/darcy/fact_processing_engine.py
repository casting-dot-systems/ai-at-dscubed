"""
This engine's job is to receive facts and decides whether to
create, update, or delete a fact.

To create or update a fact, construct the content as follows:
<CREATE_FACT><fact>

To delete a fact, construct the content as follows:
<DELETE_FACT><fact>
"""

from dataclasses import dataclass
from typing import Optional
import uuid
import json

from llmgine.llm.engine.engine import Engine
from llmgine.messages.commands import Command, CommandResult
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools import ToolCall
from llmgine.ui.cli.components import SelectPromptCommand, SelectPrompt
from custom_tools.fact_checking.functions import (
    create_fact,
    send_to_judge,
    deletion_confirmation,
    get_all_facts,
)

CREATE_FACT_TOKEN = "<CREATE_FACT>"
DELETE_FACT_TOKEN = "<DELETE_FACT>"

SYSTEM_PROMPT = (
    f"You are a fact processing engine. You will receive a new fact to create or delete, and you will also receive all facts. "
    f"Your task:"
    f"1. Choose the facts that are similar and contradictory to the new fact."
    f'2. If requested for creation and there are similar or contradictory facts, call the "send_to_judge" tool.'
    f'3. If requested for creation and there are no similar or contradictory facts, call the "create_fact" tool.'
    f'4. If requested for deletion and there are similar or contradictory facts, call "deletion_confirmation" tool.'
    f'5. If requested for deletion and there are no similar or contradictory facts, say something like "Cannot delete fact because there are no similar or contradictory facts".\n'
    f"Examples:"
    f"Example 1:"
    f'Input: "<CREATE_FACT> I love cheese. All facts: I enjoy eating cheese. I love cheese. I hate cheese."'
    f'Action: "Tool call: send_to_judge"'
    f"Example 2:"
    f'Input: "<CREATE_FACT> I love cheese. All facts: I enjoy eating beef."'
    f'Action: "Tool call: create_fact"'
    f'Output: "Created fact: I love cheese."'
    f"Example 3:"
    f'Input: "<DELETE_FACT> I love cheese. All facts: I enjoy eating cheese. I love cheese. I hate cheese."'
    f'Action: "Tool call: deletion_confirmation"'
    f'Output: "Confirmation: I love cheese."'
    f"Example 4:"
    f'Input: "<DELETE_FACT> I love cheese. All facts: I enjoy eating beef."'
    f'Action: "Tool call: deletion_confirmation"'
    f'Output: "Cannot delete fact because there are no similar or contradictory facts".\n'
)

# ----------------------------------CUSTOM DATACLASSES-----------------------------------


@dataclass
class FactProcessingEngineCommand(Command):
    prompt: str = ""


@dataclass
class FactProcessingEngineStatusEvent(Event):
    status: str = ""


@dataclass
class FactProcessingEngineToolResultEvent(Event):
    tool_name: str = ""
    result: str = ""


# ------------------------------------ENGINE-------------------------------------------


class FactProcessingEngine(Engine):
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.system_prompt = system_prompt
        self.session_id = session_id
        self.message_bus = MessageBus()

        # Create tightly coupled components - pass the simple engine
        self.context_manager = SimpleChatHistory(
            engine_id=self.engine_id, session_id=self.session_id
        )
        self.llm_manager = Gpt41Mini(Providers.OPENAI)
        self.tool_manager = ToolManager(
            engine_id=self.engine_id,
            session_id=self.session_id,
            llm_model_name="openai",
        )

    async def handle_command(
        self, command: FactProcessingEngineCommand
    ) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def __parse_prompt(self, prompt: str) -> str:
        """This function parses the prompt into a content string.
        User details are appending to the prompt.
        If the prompt contains a CREATE_FACT_TOKEN or DELETE_FACT_TOKEN,
        then all facts relating to the user are appended to the prompt.

        Args:
            prompt: The prompt to parse
        """
        content = ""
        discord_id = "774065995508744232"
        content += f"My discord id is {discord_id}. {prompt}"
        if CREATE_FACT_TOKEN in prompt or DELETE_FACT_TOKEN in prompt:
            content += get_all_facts(discord_id)

        return content

    async def execute(self, prompt: str) -> str:
        """This function executes the engine.
        General Logic Flow:
        If user wants to create a fact:
            If there are similar or contradictory facts, "send_to_judge" tool is called.
            If there are no similar or contradictory facts, "create_fact" tool is called.
        If user wants to delete a fact:
            If there are similar or contradictory facts, "deletion_confirmation" tool is called.
            If there are no similar or contradictory facts, nothing happens.

        Args:
            prompt: The prompt to execute
        """
        try:
            content = self.__parse_prompt(prompt)
        except ValueError as e:
            return str(e)

        self.context_manager.store_string(content, "user")

        while True:
            # Retrieve the current context
            current_context = await self.context_manager.retrieve()
            # Get the tools
            tools = await self.tool_manager.get_tools()
            # Notify status
            await self.message_bus.publish(
                FactProcessingEngineStatusEvent(
                    status="calling LLM", session_id=self.session_id
                )
            )
            # Generate the response
            response = await self.llm_manager.generate(
                messages=current_context, tools=tools
            )
            # Get the response message
            response_message = response.raw.choices[0].message
            # Store the response message
            await self.context_manager.store_assistant_message(response_message)
            # If there are no tool calls, break the loop and return the content
            if not response_message.tool_calls:
                final_content = response_message.content or ""
                # Notify status complete
                await self.message_bus.publish(
                    FactProcessingEngineStatusEvent(
                        status="finished", session_id=self.session_id
                    )
                )
                return final_content

            # Else, process tool calls
            for tool_call in response_message.tool_calls:
                tool_call_obj = ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                )
                try:
                    # Execute the tool
                    await self.message_bus.publish(
                        FactProcessingEngineStatusEvent(
                            status="executing tool", session_id=self.session_id
                        )
                    )

                    # Message bus is hidden from the llm, insert it here manually
                    if (
                        tool_call.function.name == "send_to_judge"
                        or tool_call.function.name == "deletion_confirmation"
                    ):
                        args = json.loads(tool_call.function.arguments)
                        args["session_id"] = self.session_id
                        tool_call_obj.arguments = json.dumps(args)

                    result = await self.tool_manager.execute_tool_call(tool_call_obj)

                    # Convert result to string if needed for history
                    if isinstance(result, dict):
                        result_str = json.dumps(result)
                    else:
                        result_str = str(result)
                    # Store tool execution result in history
                    self.context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=result_str,
                    )
                    # Publish tool execution event
                    await self.message_bus.publish(
                        FactProcessingEngineToolResultEvent(
                            tool_name=tool_call_obj.name,
                            result=result_str,
                            session_id=self.session_id,
                        )
                    )

                except Exception as e:
                    error_msg = f"Error executing tool {tool_call_obj.name}: {str(e)}"
                    print(error_msg)  # Debug print
                    # Store error result in history
                    self.context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=error_msg,
                    )

    async def register_tool(self, function):
        """Register a function as a tool.

        Args:
            function: The function to register as a tool
        """
        await self.tool_manager.register_tool(function)


async def use_fact_processing_engine(
    prompt: str, system_prompt: Optional[str] = None
):
    session_id = str(uuid.uuid4())
    engine = FactProcessingEngine(system_prompt, session_id)
    return await engine.execute(prompt)


async def main():
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent, ToolComponent
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()

    # Initialize the engine
    engine = FactProcessingEngine(
        system_prompt=SYSTEM_PROMPT,
        session_id="test",
    )

    # Register cli components
    cli = EngineCLI("test")
    cli.register_engine(engine)
    cli.register_engine_command(FactProcessingEngineCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(FactProcessingEngineStatusEvent)
    cli.register_component_event(FactProcessingEngineToolResultEvent, ToolComponent)
    cli.register_prompt_command(SelectPromptCommand, SelectPrompt)

    # Register tools
    await engine.register_tool(create_fact)
    await engine.register_tool(send_to_judge)
    await engine.register_tool(deletion_confirmation)
    await cli.main()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
