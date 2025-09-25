from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .const import DEFAULT_BASE_VERSION, DEFAULT_CATEGORY, DEFAULT_TYPE
from .mkd import normalize_title_id, build_new_note_text, read_note, split_frontmatter, ensure_footer_blocks
from .types import DiffResult
from .utils import now_timestamp_str, read_text, write_text, run_in_thread


async def create_note(
    root: str | Path,
    title: str,
    content: str = "",
    frontmatter: Optional[Dict] = None,
    dependencies: Optional[List[str]] = None,
    overwrite: bool = False,
) -> Dict:
    root = Path(root)
    norm = normalize_title_id(title)
    path = root / f"{norm}.md"
    if path.exists() and not overwrite:
        return {"created": False, "path": str(path), "reason": "exists"}
    fm = {
        "last-updated": now_timestamp_str(),
        "category": DEFAULT_CATEGORY,
        "type": DEFAULT_TYPE,
        "base-version": DEFAULT_BASE_VERSION,
    }
    fm.update(frontmatter or {})
    text = build_new_note_text(fm, content, dependencies)
    await run_in_thread(write_text, path, text)
    return {"created": True, "path": str(path), "title": norm}


async def edit_replace(
    root: str | Path,
    find: str,
    replace: str,
    regex: bool = False,
    case_sensitive: bool | None = None,
    include_glob: str = "**/*.md",
    paths: Optional[List[str]] = None,
    dry_run: bool = True,
    max_files: int = 1000,
) -> Dict:
    root = Path(root)
    if paths:
        targets = [Path(p) for p in paths]
    else:
        targets = await run_in_thread(lambda: list(root.glob(include_glob)))
    flags = 0
    if case_sensitive is False:
        flags |= re.IGNORECASE
    pattern = re.compile(find if regex else re.escape(find), flags)
    changed: List[Dict] = []

    for p in targets[:max_files]:
        if not p.is_file():
            continue
        text = await run_in_thread(read_text, p)
        new_text, n = pattern.subn(replace, text)
        if n > 0:
            # bump last-updated in frontmatter if present
            fm, body = split_frontmatter(new_text)
            if fm:
                fm["last-updated"] = now_timestamp_str()
                from .mkd import make_frontmatter  # local import to avoid cycle
                new_text = make_frontmatter(fm) + body
            diff = await make_diff(str(p), text, new_text)
            changed.append({"path": str(p), "replacements": n, "diff": diff.diff_unified})
            if not dry_run:
                await run_in_thread(write_text, p, new_text)

    return {"ok": True, "changed": changed, "dry_run": dry_run}


async def rename_title(
    root: str | Path,
    old_title: str,
    new_title: str,
    update_links: bool = True,
    include_glob: str = "**/*.md",
) -> Dict:
    root = Path(root)
    old_norm = normalize_title_id(old_title)
    new_norm = normalize_title_id(new_title)
    old_path = root / f"{old_norm}.md"
    new_path = root / f"{new_norm}.md"
    if not old_path.exists():
        return {"ok": False, "error": f"not found: {old_path}"}
    if new_path.exists():
        return {"ok": False, "error": f"target exists: {new_path}"}

    # rename file
    await run_in_thread(old_path.rename, new_path)
    updated_files = []

    if update_links:
        pattern = re.compile(r"\[\[(" + re.escape(old_norm) + r")(?P<rest>[^\]]*)\]\]")
        targets = await run_in_thread(lambda: list(root.glob(include_glob)))
        for p in targets:
            if not p.is_file():
                continue
            text = await run_in_thread(read_text, p)
            # replace only the title part before '#|'
            def _repl(m):
                rest = m.group("rest") or ""
                # keep section or alias tails intact
                return f"[[{new_norm}{rest}]]"

            new_text, n = pattern.subn(_repl, text)
            if n > 0:
                from .mkd import split_frontmatter, make_frontmatter
                fm, body = split_frontmatter(new_text)
                if fm:
                    fm["last-updated"] = now_timestamp_str()
                    new_text = make_frontmatter(fm) + body
                await run_in_thread(write_text, p, new_text)
                updated_files.append({"path": str(p), "updates": n})

    return {"ok": True, "old_title": old_norm, "new_title": new_norm, "path": str(new_path), "link_updates": updated_files}


async def make_diff(label: str, old_text: str, new_text: str) -> DiffResult:
    import difflib
    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=label + " (old)",
        tofile=label + " (new)",
        n=3,
    )
    from .types import DiffResult
    return DiffResult(a_label=label + " (old)", b_label=label + " (new)", diff_unified="".join(diff))