from dataclasses import dataclass
from typing import Any, Dict, List, NewType

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.llm.providers.openai import OpenAIProvider
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools.tool_manager import (
    ToolManager, ToolCall
)
from llmgine.messages import Command, CommandResult, Event 

from groupfunctions import GroupFunctions
    
import asyncio
import uuid
import os
import dotenv 
import json

dotenv.load_dotenv()
DiscordChannelID = NewType("DiscordChannelID", str)

@dataclass
class TeamAssignmentCommand(Command):
    """Command to assign users to groups"""

    prompt: str = ""

@dataclass
class TeamAssignmentEngineStatusEvent(Event):
    """Event to get the status of the team assignment engine"""

    status: str = ""

@dataclass
class TeamAssignmentEngineToolResultEvent(Event):
    """Event to get the result of the tool call"""

    tool_name: str = ""
    result: str = ""

class TeamAssignmentEngine:
    def __init__(
            self, system_prompt: str, session_id: SessionID, channel_id: DiscordChannelID
    ):
        self.bus = MessageBus()
        self.session_id = session_id
        self.channel_id = channel_id 
        self.system_prompt = system_prompt
        self.engine_id = str(uuid.uuid4())
        self.model = OpenAIProvider(
            model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY")
        )
        self.context_manager: SimpleChatHistory = SimpleChatHistory(
            engine_id = self.engine_id, session_id = self.session_id
        )
        self.tool_manager: ToolManager = ToolManager(
            engine_id = self.engine_id, 
            session_id = self.session_id,
            llm_model_name = "openai"
        )
        self.context_manager.set_system_prompt(self.system_prompt)
        self.group_functions = GroupFunctions()

    async def extract_conversation(self) -> list[Dict[str, Any]]:
        """Extract the conversation from the context manager"""
        conversation = await self.context_manager.retrieve()
        return conversation 
    
    async def handle_command(self, command:TeamAssignmentCommand) -> CommandResult:
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
                    TeamAssignmentEngineStatusEvent(
                        status="Calling LLM",
                        session_id=self.session_id,
                    )
                )
                response = await self.model.generate(
                    messages=current_context, tools=tools
                )
                
                response_message = response.raw.choices[0].message
                await self.context_manager.store_assistant_message(response_message)

        #         if not response_message.tool_calls:
        #             final_content = response_message.content or ""
        #             await self.bus.publish(
        #                 TeamAssignmentEngineStatusEvent(
        #                     status="finished",
        #                     session_id=self.session_id,
        #                 )
        #             )
        #             return CommandResult(success=True, result=final_content)
                
        #         tool_calls = response_message.tool_calls
        #         for tool_call in tool_calls:
        #             await self.bus.publish(
        #                 TeamAssignmentEngineStatusEvent(
        #                     status="Executing tool call",
        #                     session_id=self.session_id,
        #                 )
        #             )

        #             tool_call_obj = ToolCall(
        #                 id=tool_call.id,
        #                 name=tool_call.function.name,
        #                 arguments=tool_call.function.arguments,
        #             )

        #             tool_call_obj.session_id = self.session_id
        #             tool_result = await self.tool_manager.execute_tool_call(tool_call_obj)

        #             self.context_manager.store_tool_call_result(
        #             tool_call_id=tool_call_obj.id,
        #             name=tool_call_obj.name,
        #             content=tool_result.result,
        #         )

        #             await self.bus.publish(
        #             TeamAssignmentEngineToolResultEvent(
        #                 tool_name=tool_call_obj.name, 
        #                 result=tool_result.result,
        #             )
        #         )

        #         tool_call_count += 1
        #         if tool_call_count > max_tool_calls:
        #             raise RuntimeError("Tool call limit reached")

        # except Exception as e:
        #     return CommandResult(
        #         success=False,
        #         result=f"Error: {str(e)}"
        #     )
        
                if not response_message.tool_calls:
                    # No tool calls, break the loop and return the content
                    final_content = response_message.content or ""

                    # Notify status complete
                    await self.bus.publish(
                        TeamAssignmentEngineStatusEvent(
                            status="finished", session_id=self.session_id
                        )
                    )
                    return CommandResult(
                        success=True, result=final_content, session_id=self.session_id
                    )

                # 8. Process tool calls
                for tool_call in response_message.tool_calls:
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                    try:
                        # Execute the tool
                        await self.bus.publish(
                            TeamAssignmentEngineStatusEvent(
                                status="executing tool", session_id=self.session_id
                            )
                        )

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
                        await self.bus.publish(
                            TeamAssignmentEngineToolResultEvent(
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
                # After processing all tool calls, loop back to call the LLM again
                # with the updated context (including tool results).

        except Exception as e:
            # Log the exception before returning
            # logger.exception(f"Error in handle_prompt_command for session {self.session_id}") # Requires logger setup
            print(f"ERROR in handle_prompt_command: {e}")  # Simple print for now
            import traceback

            traceback.print_exc()  # Print stack trace

            return CommandResult(success=False, error=str(e), session_id=self.session_id)

        
async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import (
        EngineResultComponent,
        ToolComponentShort,
    )

    app = ApplicationBootstrap(ApplicationConfig(enable_console_handler=False))
    await app.bootstrap()
    cli = EngineCLI("test")
    engine = TeamAssignmentEngine(
        system_prompt=f"""
            You are a team assignment assistant. You are responsible for creating groups and assigning users to their assigned group(s).
            These are the tools you can use:
            - create_group: Create a new group
            - get_group: Get a group by group id (use `get_group_id` to get the group id)
            - delete_group: First remove all members in the group (using modify_group) then delete a group by group id (use `get_group_id` to get the group id), if the user ask you to delete all groups, you should get all groups by 'get_all_groups' and delete them one by one.
            - modify_group: Add or remove users to a group by calling `get_group_id` and `get_user_id` to get the group id and user id respectively.
            Use these tools whenever appropriate, based on the user's request. If the user asks you to create a group, you can call `create_group` even without any users. Only use `modify_group` when assigning or removing users.
        """, 
        session_id="test", 
        channel_id="test",
    )

    for function in [
        engine.group_functions.create_group,
        engine.group_functions.get_group,
        engine.group_functions.delete_group,
        engine.group_functions.modify_group,
        engine.group_functions.get_group_id,
        engine.group_functions.get_user_id,
        engine.group_functions.get_all_groups,
    ]:
        await engine.tool_manager.register_tool(function)

    cli.register_engine(engine)
    cli.register_engine_command(TeamAssignmentCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(TeamAssignmentEngineStatusEvent)
    cli.register_component_event(TeamAssignmentEngineToolResultEvent, ToolComponentShort)
    await cli.main()

if __name__ == "__main__":
    asyncio.run(main())