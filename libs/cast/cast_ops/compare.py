from __future__ import annotations

import difflib
from pathlib import Path
from typing import Dict, Tuple

from .mkd import split_frontmatter
from .types import DiffResult
from .utils import read_text, run_in_thread


async def compare_files(a_path: str | Path, b_path: str | Path, context_lines: int = 3) -> DiffResult:
    a = Path(a_path)
    b = Path(b_path)
    a_text, b_text = await run_in_thread(read_text, a), await run_in_thread(read_text, b)
    return unified_diff(a_text, b_text, str(a), str(b), context_lines)


async def compare_text(a_label: str, a_text: str, b_label: str, b_text: str, context_lines: int = 3) -> DiffResult:
    return unified_diff(a_text, b_text, a_label, b_label, context_lines)


def unified_diff(a_text: str, b_text: str, a_label: str, b_label: str, n: int) -> DiffResult:
    diff = difflib.unified_diff(
        a_text.splitlines(keepends=True),
        b_text.splitlines(keepends=True),
        fromfile=a_label,
        tofile=b_label,
        n=n,
    )
    return DiffResult(a_label=a_label, b_label=b_label, diff_unified="".join(diff))


async def compare_frontmatter(a_path: str | Path, b_path: str | Path) -> Dict:
    a = Path(a_path)
    b = Path(b_path)
    a_raw, b_raw = await run_in_thread(read_text, a), await run_in_thread(read_text, b)
    a_fm, _ = split_frontmatter(a_raw)
    b_fm, _ = split_frontmatter(b_raw)
    keys = set(a_fm.keys()) | set(b_fm.keys())
    delta = {}
    for k in sorted(keys):
        if a_fm.get(k) != b_fm.get(k):
            delta[k] = {"a": a_fm.get(k), "b": b_fm.get(k)}
    return delta