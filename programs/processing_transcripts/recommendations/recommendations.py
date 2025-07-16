import os
import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich import box
import re
import json as pyjson

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

console = Console()

@dataclass
class RecommendTasksCommand(Command):
    transcript_path: str = ""
    tasks: Optional[List[Dict[str, Any]]] = None  # [{task, person, editable}]
    confirmed: bool = False

@dataclass
class RecommendTasksStatusEvent(Event):
    status: str = ""

@dataclass
class RecommendTasksResultEvent(Event):
    result: str = ""

class RecommendationsEngine:
    def __init__(self, model: Any, session_id: Optional[SessionID] = None):
        self.model = model
        self.session_id = session_id or SessionID(str(uuid.uuid4()))
        self.bus = MessageBus()
        self.engine_id = str(uuid.uuid4())
        self.tasks: List[Dict[str, Any]] = []
        self.future_steps: List[str] = []
        self.project_name: Optional[str] = None
        self.project_people: List[str] = []

    async def handle_command(self, command: Command) -> CommandResult:
        try:
            if isinstance(command, RecommendTasksCommand):
                transcript_path = command.transcript_path
                tasks = command.tasks
                confirmed = command.confirmed
            else:
                transcript_path = getattr(command, 'transcript_path', None)
                tasks = getattr(command, 'tasks', None)
                confirmed = getattr(command, 'confirmed', False)
                if not transcript_path:
                    raise ValueError("No transcript_path provided in command.")
            if not tasks:
                await self.extract_and_recommend_tasks(transcript_path)
                return CommandResult(success=True, result=self.format_tasks_for_review(), session_id=self.session_id)
            elif not confirmed:
                return CommandResult(success=True, result=self.format_tasks_for_review(), session_id=self.session_id)
            else:
                return CommandResult(success=True, result=self.format_final_assignments(), session_id=self.session_id)
        except Exception as e:
            return CommandResult(success=False, error=str(e), session_id=self.session_id)

    async def extract_and_recommend_tasks(self, transcript_path: str):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        with open(PROJECTS_SQL_PATH, 'r', encoding='utf-8') as f:
            project_info = f.read()
        prompt = (
            "You are an expert project manager assistant. "
            "Given the following meeting transcript and project information, extract a list of recommended tasks for people. "
            "Assign tasks to people based on info from the transcript. If a task cannot be assigned, recommend people from the project team in the project info. "
            "Output ONLY valid JSON in the following format: {\"tasks\": [{\"task\": ..., \"person\": ..., \"reasoning\": ...}], \"future_steps\": [list of follow-up or next steps for the project or people after these tasks are completed], \"project_name\": ..., \"project_people\": [list of people]}"
            f"\n\nProject Info (from SQL):\n{project_info}\n\nMeeting Transcript:\n{transcript}\n\nJSON:"
        )
        response = await self.model.generate(messages=[{"role": "user", "content": prompt}])
        content = response.raw.choices[0].message.content or ""
        import re
        import json as pyjson
        try:
            # Remove markdown code block markers if present
            content_clean = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            # Extract the first JSON object from the cleaned content
            match = re.search(r'({[\s\S]+})', content_clean)
            json_str = match.group(1) if match else content_clean
            data = pyjson.loads(json_str)
            self.tasks = data.get("tasks", [])
            self.future_steps = data.get("future_steps", [])
            self.project_name = data.get("project_name", None)
            self.project_people = data.get("project_people", [])
        except Exception:
            # Fallback: try to extract tasks as lines
            self.tasks = []
            self.future_steps = []
            self.project_name = None
            self.project_people = []
            # Try to find lines that look like tasks
            for line in content.splitlines():
                if line.strip().startswith("-") or line.strip().startswith("*"):
                    self.tasks.append({"task": line.strip("-* ")})

    def format_tasks_for_review(self) -> str:
        if not self.tasks:
            return "No tasks found."
        out = ["Recommended tasks and assignments:\n"]
        for idx, t in enumerate(self.tasks, 1):
            out.append(f"[{idx}] Task: {t.get('task','') or t.get('Task','') or str(t)}\n    Assigned to: {t.get('person','(unassigned)') or t.get('Person','(unassigned)')}\n    Reasoning: {t.get('reasoning','') or t.get('Reasoning','')}")
        out.append("\nYou can edit a task or assignee by entering the task number, or type 'confirm' to lock in assignments.")
        return "\n".join(out)

    def format_final_assignments(self) -> str:
        if not self.tasks:
            return "No tasks assigned."
        assignments: Dict[str, List[str]] = {}
        for t in self.tasks:
            person = t.get('person', '(unassigned)') or t.get('Person', '(unassigned)')
            assignments.setdefault(person, []).append(t.get('task','') or t.get('Task','') or str(t))
        out = ["Final task assignments:\n"]
        for person, tasks in assignments.items():
            out.append(f"{person}:")
            for task in tasks:
                out.append(f"  - {task}")
        if self.future_steps:
            out.append("\nRecommended future steps:")
            for step in self.future_steps:
                out.append(f"  - {step}")
        return "\n".join(out)


def list_transcripts() -> List[str]:
    return [os.path.join(TRANSCRIPTS_DIR, f) for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.txt')]

async def main():
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    model = Gpt41Mini(Providers.OPENAI)
    engine = RecommendationsEngine(model)
    cli = EngineCLI(engine.session_id)
    cli.register_engine(engine)
    cli.register_engine_command(RecommendTasksCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    # Transcript selection prompt
    transcripts = list_transcripts()
    console.print(Panel("[bold cyan]Meeting Transcript Recommendations Engine[/bold cyan]", expand=False))
    console.print("[bold]Available transcripts:[/bold]")
    for idx, path in enumerate(transcripts, 1):
        console.print(f"  [cyan][{idx}][/cyan] {os.path.basename(path)}")
    while True:
        try:
            choice = Prompt.ask(f"Select transcript [1-{len(transcripts)}]")
            choice = int(choice)
            if 1 <= choice <= len(transcripts):
                break
            else:
                console.print("[red]Invalid choice. Try again.[/red]")
        except Exception:
            console.print("[red]Invalid input. Enter a number.[/red]")
    transcript_path = transcripts[choice - 1]
    # Step 1: Extract and review tasks
    command = RecommendTasksCommand(transcript_path=transcript_path)
    result = await engine.handle_command(command)
    while True:
        console.clear()
        console.print(Panel("[bold cyan]Review and Edit Task Assignments[/bold cyan]", expand=False))
        console.print(result.result)
        if "no tasks found" in str(result.result).lower():
            Prompt.ask("[bold red]Press Enter to exit[/bold red]")
            return  # Exit the program if no tasks are found
        user_input = Prompt.ask("[bold yellow]Enter task number to edit, or type 'confirm' to lock in assignments[/bold yellow]", default="confirm").strip().lower()
        if user_input == 'confirm':
            confirm_command = RecommendTasksCommand(transcript_path=transcript_path, tasks=engine.tasks, confirmed=True)
            result = await engine.handle_command(confirm_command)
            break
        elif user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(engine.tasks):
                console.print(Panel(f"Editing Task {idx+1}: {engine.tasks[idx].get('task','')}", expand=False))
                new_task = Prompt.ask("Enter new task description (or press Enter to keep)", default=engine.tasks[idx]['task']).strip()
                new_person = Prompt.ask("Enter new assignee (or press Enter to keep)", default=engine.tasks[idx].get('person','')).strip()
                if new_task:
                    engine.tasks[idx]['task'] = new_task
                if new_person:
                    engine.tasks[idx]['person'] = new_person
                # Re-run review
                review_command = RecommendTasksCommand(transcript_path=transcript_path, tasks=engine.tasks, confirmed=False)
                result = await engine.handle_command(review_command)
            else:
                console.print("[red]Invalid task number.[/red]")
        else:
            console.print("[red]Invalid input.[/red]")
    console.clear()
    console.print(Panel("[bold green]Final Assignments & Future Steps[/bold green]", expand=False))
    console.print(result.result)

if __name__ == "__main__":
    asyncio.run(main())
