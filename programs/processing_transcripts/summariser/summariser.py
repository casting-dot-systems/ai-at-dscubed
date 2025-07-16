import os
import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Optional, List

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.ui.cli.cli import EngineCLI
from llmgine.ui.cli.components import EngineResultComponent

TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../brain/processing_transcripts_info/transcripts/cleaned'))
PROJECTS_SQL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../brain/processing_transcripts_info/DML/sample_projects.sql'))

@dataclass
class SummariseTranscriptCommand(Command):
    transcript_path: str = ""

@dataclass
class SummariseTranscriptStatusEvent(Event):
    status: str = ""

@dataclass
class SummariseTranscriptResultEvent(Event):
    summary: str = ""

class SummariserEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(uuid.uuid4())

    async def handle_command(self, command: Command) -> CommandResult:
        try:
            # Accept base Command, cast to SummariseTranscriptCommand
            if isinstance(command, SummariseTranscriptCommand):
                transcript_path = command.transcript_path
            else:
                transcript_path = getattr(command, 'transcript_path', None)
                if not transcript_path:
                    raise ValueError("No transcript_path provided in command.")
            summary = await self.summarise(transcript_path)
            return CommandResult(success=True, result=summary, session_id=self.session_id)
        except Exception as e:
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def summarise(self, transcript_path: str) -> str:
        await self.bus.publish(SummariseTranscriptStatusEvent(status="Reading transcript and project info", session_id=self.session_id))
        # Read transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        # Read project info
        with open(PROJECTS_SQL_PATH, 'r', encoding='utf-8') as f:
            project_info = f.read()
        await self.bus.publish(SummariseTranscriptStatusEvent(status="Generating summary via GPT-4.1", session_id=self.session_id))
        prompt = (
            "You are an expert meeting summariser. "
            "Given the following meeting transcript and project information, "
            "write a concise but detailed summary of the meeting. "
            "Clearly list the points mentioned, and disregard any information that can 100% be classified as irrelevant. "
            "If possible, relate the discussion to the project(s) referenced.\n\n"
            f"Project Info (from SQL):\n{project_info}\n\n"
            f"Meeting Transcript:\n{transcript}\n\n"
            "Summary:"
        )
        response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
        # Extract summary from response
        summary = response.raw.choices[0].message.content or "(No summary returned)"
        await self.bus.publish(SummariseTranscriptResultEvent(summary=summary, session_id=self.session_id))
        await self.bus.publish(SummariseTranscriptStatusEvent(status="finished", session_id=self.session_id))
        return summary

def list_transcripts() -> List[str]:
    return [os.path.join(TRANSCRIPTS_DIR, f) for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.txt')]

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    model = Gpt41Mini(Providers.OPENAI)
    engine = SummariserEngine(model)
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(SummariseTranscriptCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(SummariseTranscriptStatusEvent)
    # Transcript selection prompt
    transcripts = list_transcripts()
    print("Available transcripts:")
    for idx, path in enumerate(transcripts, 1):
        print(f"  [{idx}] {os.path.basename(path)}")
    while True:
        try:
            choice = int(input(f"Select transcript [1-{len(transcripts)}]: "))
            if 1 <= choice <= len(transcripts):
                break
            else:
                print("Invalid choice. Try again.")
        except Exception:
            print("Invalid input. Enter a number.")
    transcript_path = transcripts[choice - 1]
    # Run the engine with the selected transcript
    command = SummariseTranscriptCommand(transcript_path=transcript_path)
    result = await engine.handle_command(command)
    print("\n===== SUMMARY =====\n")
    print(result.result if result.success else f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
