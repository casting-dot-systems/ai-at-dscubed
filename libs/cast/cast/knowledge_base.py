from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List

from litellm import acompletion


CAST_FOLDER_ENV = "CAST_FOLDER"


def _load_cast_folder() -> Path:
    cast_folder = os.getenv(CAST_FOLDER_ENV)
    if not cast_folder:
        raise RuntimeError(f"{CAST_FOLDER_ENV} environment variable not set")

    cast_path = Path(cast_folder)
    if not cast_path.exists():
        raise RuntimeError(f"Cast folder '{cast_folder}' does not exist")

    return cast_path


def _iter_markdown_files(cast_path: Path) -> Iterable[Path]:
    return cast_path.glob("*.md")


def _preview_file(md_file: Path, preview_lines: int = 3, max_preview_len: int = 200) -> str:
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - file system issue
        return f"- {md_file.name}: Error reading file - {exc}"

    lines = content.splitlines()
    preview = " ".join(lines[:preview_lines])
    if len(preview) > max_preview_len:
        preview = preview[:max_preview_len] + "..."
    return f"- {md_file.name}: {preview}"


def _build_files_list(cast_path: Path) -> str:
    md_files = list(_iter_markdown_files(cast_path))
    if not md_files:
        return ""

    previews = [_preview_file(md_file) for md_file in md_files]
    return "\n".join(previews)


def _parse_llm_list(raw_response: str) -> List[str]:
    clean_result = raw_response.strip()
    if "[" in clean_result and "]" in clean_result:
        start = clean_result.find("[")
        end = clean_result.rfind("]") + 1
        clean_result = clean_result[start:end]
    try:
        parsed = json.loads(clean_result)
    except json.JSONDecodeError as exc:  # pragma: no cover - depends on LLM response
        raise RuntimeError(f"Error parsing file selection response: {exc}. Raw response: {raw_response[:200]}...")
    if not isinstance(parsed, list):  # pragma: no cover - defensive
        raise RuntimeError("Error: LLM did not return a valid list of files")
    return [str(item) for item in parsed]


async def cast_find_relevant_files(query: str, *, max_files: int = 5) -> str:
    """Find the most relevant Cast files for a given query."""
    try:
        cast_path = _load_cast_folder()
    except RuntimeError as exc:
        return str(exc)
    files_list = _build_files_list(cast_path)
    if not files_list:
        return "No markdown files found in Cast folder"

    selection_prompt = f"""Given this query: "{query}"

Here are the available Cast files with previews:
{files_list}

Select the {max_files} most relevant files for answering this query. Return only a JSON list of filenames, like: ["file1.md", "file2.md"].

Consider:
- Semantic relevance to the query
- Conceptual relationships
- Potential for containing useful context

Response (JSON only):"""

    response = await acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": selection_prompt}],
        temperature=0.1,
    )
    if not response.choices:
        return "Error: No response from LLM for file selection"

    result = response.choices[0].message.content
    if not result:
        return "Error: Empty response from LLM"

    try:
        selected_files = _parse_llm_list(result)
    except RuntimeError as exc:
        return str(exc)

    return f"Selected files: {json.dumps(selected_files)}"


async def cast_retrieve_and_answer(query: str, selected_files: Iterable[str]) -> str:
    """Retrieve content from selected Cast files and answer the query using that context."""
    try:
        cast_path = _load_cast_folder()
    except RuntimeError as exc:
        return str(exc)

    context_content = []
    for filename in selected_files:
        file_path = cast_path / filename
        if not file_path.exists():
            context_content.append(f"=== {filename} ===\nFile not found\n")
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - file system issue
            context_content.append(f"=== {filename} ===\nError reading file: {exc}\n")
            continue
        context_content.append(f"=== {filename} ===\n{content}\n")

    combined_context = "\n".join(context_content)

    answer_prompt = f"""Using the following Cast documentation as context, answer this query: "{query}"

Cast Context:
{combined_context}

Instructions:
- Use the Cast context to inform your answer
- Reference specific information from the files when relevant
- If the context doesn't contain relevant information, say so
- Provide a comprehensive answer based on the available context

Answer:"""

    response = await acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": answer_prompt}],
        temperature=0.3,
    )
    if not response.choices:
        return "Error: No response from LLM for answering query"

    result = response.choices[0].message.content
    if not result:
        return "Error: Empty response from LLM"

    return result


async def cast_query(query: str, *, max_files: int = 5) -> str:
    """Query the Cast knowledge base to retrieve relevant file contents."""
    try:
        cast_path = _load_cast_folder()
    except RuntimeError as exc:
        return str(exc)
    files_list = _build_files_list(cast_path)
    if not files_list:
        return "No markdown files found in Cast folder"

    selection_prompt = f"""Given this query: "{query}"

Here are the available Cast files with previews:
{files_list}

Select the {max_files} most relevant files for answering this query. Return only a JSON list of filenames, like: ["file1.md", "file2.md"].

Response (JSON only):"""

    response = await acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": selection_prompt}],
        temperature=0.1,
    )
    if not response.choices:
        return "Error: No response from LLM for file selection"

    result = response.choices[0].message.content
    if not result:
        return "Error: Empty response from LLM"

    try:
        selected_files = _parse_llm_list(result)
    except RuntimeError as exc:
        return str(exc)

    context_content = [f"Retrieved {len(selected_files)} relevant Cast files for query: '{query}'\n"]
    for filename in selected_files:
        file_path = cast_path / filename
        if not file_path.exists():
            context_content.append(f"=== {filename} ===\nFile not found\n")
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - file system issue
            context_content.append(f"=== {filename} ===\nError reading file: {exc}\n")
            continue
        context_content.append(f"=== {filename} ===\n{content}\n")

    return "\n".join(context_content)
