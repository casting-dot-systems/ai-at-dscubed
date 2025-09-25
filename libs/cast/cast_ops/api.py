from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .compare import compare_files, compare_frontmatter, compare_text
from .edit import create_note, edit_replace, rename_title
from .indexer import CastIndex
from .mkd import read_note, ensure_footer_blocks, parse_dependencies
from .search import fuzzy_title_search, grep_content, hybrid_search
from .types import to_json_safe
from .utils import run_in_thread


# ---------------------------
# Helper to standardize result
# ---------------------------
def _ok(data: Any, meta: Dict | None = None) -> Dict:
    return {"ok": True, "data": to_json_safe(data), "error": None, "meta": meta or {}}


def _err(msg: str, meta: Dict | None = None) -> Dict:
    return {"ok": False, "data": None, "error": msg, "meta": meta or {}}


# ---------------------------
# Public async API (tool-call)
# ---------------------------

async def cast_search_titles_fuzzy(root: str, query: str, limit: int = 20, threshold: float = 55.0) -> Dict:
    try:
        hits = await fuzzy_title_search(root, query, limit=limit, threshold=threshold)
        return _ok([h.__dict__ for h in hits])
    except Exception as e:
        return _err(str(e))


async def cast_grep(
    root: str,
    query: str,
    regex: bool = False,
    case_sensitive: Optional[bool] = None,
    context_lines: int = 0,
    limit: int = 2000,
) -> Dict:
    try:
        hits = await grep_content(root, query, regex=regex, case_sensitive=case_sensitive, context_lines=context_lines, limit=limit)
        return _ok([h.__dict__ for h in hits])
    except Exception as e:
        return _err(str(e))


async def cast_search_all(root: str, query: str, limit: int = 25) -> Dict:
    try:
        hits = await hybrid_search(root, query, limit=limit)
        return _ok([h.__dict__ for h in hits])
    except Exception as e:
        return _err(str(e))


async def cast_read_note(root: str, title_or_path: str) -> Dict:
    try:
        p = Path(title_or_path)
        if p.suffix.lower() != ".md":
            p = Path(root) / f"{title_or_path}.md"
        fm, body, raw = await run_in_thread(read_note, p)
        deps = parse_dependencies(body)
        main_content = body.split("\n" + "# =============", 1)[0] if "# =============" in body else body
        return _ok({"path": str(p), "title": p.stem, "frontmatter": fm, "content": main_content, "dependencies": deps})
    except Exception as e:
        return _err(str(e))


async def cast_build_index(root: str) -> Dict:
    try:
        idx = CastIndex(root)
        await idx.build()
        out = [n.__dict__ for n in idx.all()]
        return _ok(out, meta={"count": len(out)})
    except Exception as e:
        return _err(str(e))


async def cast_create_note(
    root: str,
    title: str,
    content: str = "",
    frontmatter: Optional[Dict[str, Any]] = None,
    dependencies: Optional[List[str]] = None,
    overwrite: bool = False,
) -> Dict:
    try:
        result = await create_note(root, title, content, frontmatter, dependencies, overwrite)
        if not result.get("created"):
            return _err(f"create failed: {result.get('reason')}", meta=result)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def cast_edit_replace(
    root: str,
    find: str,
    replace: str,
    regex: bool = False,
    case_sensitive: Optional[bool] = None,
    include_glob: str = "**/*.md",
    paths: Optional[List[str]] = None,
    dry_run: bool = True,
    max_files: int = 1000,
) -> Dict:
    try:
        res = await edit_replace(
            root=root,
            find=find,
            replace=replace,
            regex=regex,
            case_sensitive=case_sensitive,
            include_glob=include_glob,
            paths=paths,
            dry_run=dry_run,
            max_files=max_files,
        )
        return _ok(res)
    except Exception as e:
        return _err(str(e))


async def cast_rename_title(
    root: str,
    old_title: str,
    new_title: str,
    update_links: bool = True,
    include_glob: str = "**/*.md",
) -> Dict:
    try:
        res = await rename_title(root, old_title, new_title, update_links, include_glob)
        if not res.get("ok"):
            return _err(res.get("error", "rename failed"), meta=res)
        return _ok(res)
    except Exception as e:
        return _err(str(e))


async def cast_compare_files(a_path: str, b_path: str, context_lines: int = 3) -> Dict:
    try:
        diff = await compare_files(a_path, b_path, context_lines)
        return _ok(diff.__dict__)
    except Exception as e:
        return _err(str(e))


async def cast_compare_text(a_label: str, a_text: str, b_label: str, b_text: str, context_lines: int = 3) -> Dict:
    try:
        diff = await compare_text(a_label, a_text, b_label, b_text, context_lines)
        return _ok(diff.__dict__)
    except Exception as e:
        return _err(str(e))


async def cast_compare_frontmatter(a_path: str, b_path: str) -> Dict:
    try:
        delta = await compare_frontmatter(a_path, b_path)
        return _ok(delta)
    except Exception as e:
        return _err(str(e))


async def cast_validate_note(root: str, title_or_path: str) -> Dict:
    """Check MKD conformance: frontmatter exists, footer blocks exist, End sentinel present."""
    from .mkd import split_frontmatter, ensure_footer_blocks
    try:
        p = Path(title_or_path)
        if p.suffix.lower() != ".md":
            p = Path(root) / f"{title_or_path}.md"
        raw = Path(p).read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(raw)
        issues = []
        if not fm:
            issues.append("missing frontmatter or malformed YAML")
        if "# End" not in body:
            issues.append("missing '# End' sentinel")
        if "# Dependencies" not in body:
            issues.append("missing '# Dependencies' section")
        if "# =============" not in body:
            issues.append("missing '# =============' separator")
        return _ok({"path": str(p), "ok": len(issues) == 0, "issues": issues})
    except Exception as e:
        return _err(str(e))


async def cast_context_bundle(
    root: str,
    query: str,
    strategy: str = "hybrid",     # "title" | "content" | "hybrid"
    top_k: int = 8,
    include_dependencies: bool = True,
) -> Dict:
    """Return a bundle of small context docs for top matches: frontmatter + main content + deps."""
    try:
        if strategy == "title":
            hits = await fuzzy_title_search(root, query, limit=top_k)
        elif strategy == "content":
            hits = await grep_content(root, query, regex=False, case_sensitive=None, limit=top_k)
        else:
            hits = await hybrid_search(root, query, limit=top_k)
        out = []
        for h in hits:
            fm, body, raw = await run_in_thread(read_note, Path(h.path))
            content = body.split("\n# =============", 1)[0] if "# =============" in body else body
            deps = parse_dependencies(body) if include_dependencies else []
            out.append({
                "title": h.title,
                "path": h.path,
                "frontmatter": fm,
                "content": content.strip(),
                "dependencies": deps,
                "score": h.score,
                "reason": h.reason,
                "snippets": [s.__dict__ for s in h.snippets],
            })
        return _ok(out, meta={"count": len(out)})
    except Exception as e:
        return _err(str(e))