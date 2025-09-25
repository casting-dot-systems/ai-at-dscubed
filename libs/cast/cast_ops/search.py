from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Tuple

from .const import MD_GLOB
from .types import MatchSnippet, SearchHit
from .utils import fuzzy_score, has_ripgrep, read_text, run_in_thread, run_ripgrep


def _collect_snippets_for_pattern(text: str, pattern: re.Pattern, max_snips: int = 6) -> List[MatchSnippet]:
    out: List[MatchSnippet] = []
    lines = text.splitlines()
    for i, ln in enumerate(lines, start=1):
        for m in pattern.finditer(ln):
            if len(out) >= max_snips:
                break
            out.append(MatchSnippet(line_no=i, line=ln, match_start=m.start(), match_end=m.end()))
    return out


async def fuzzy_title_search(root: str | Path, query: str, limit: int = 20, threshold: float = 55.0) -> List[SearchHit]:
    root = Path(root)
    paths = await run_in_thread(lambda: list(root.glob(MD_GLOB)))
    hits: List[SearchHit] = []
    q = (query or "").strip()
    for p in paths:
        title = p.stem
        sc = fuzzy_score(q, title)
        if sc >= threshold:
            hits.append(SearchHit(title=title, path=str(p), score=sc, reason="title", snippets=[]))
    hits.sort(key=lambda h: (-h.score, h.title.lower()))
    return hits[:limit]


async def grep_content(root: str | Path, query: str, regex: bool = False, case_sensitive: bool | None = None,
                       context_lines: int = 0, limit: int = 2000) -> List[SearchHit]:
    """Grep-like search across md files. Uses ripgrep if available, else Python regex scan."""
    root = Path(root)
    q = query if regex else re.escape(query)
    flags = 0
    if case_sensitive is False:
        flags |= re.IGNORECASE
    pattern = re.compile(q, flags)

    hits: List[SearchHit] = []
    use_rg = has_ripgrep()
    if use_rg:
        rg_flags: List[str] = ["-n", "-H", "-S"]  # smart case by default
        if regex:
            rg_flags.append("-e")
        else:
            rg_flags.extend(["-F", "-e"])  # fixed string
        if case_sensitive is True:
            rg_flags.append("-s")
        elif case_sensitive is False:
            rg_flags.append("-i")
        code, out, _err = await run_in_thread(run_ripgrep, root, query, rg_flags)
        # Parse rg output: path:line:match
        # We'll still re-open files to generate snippets for consistency
        seen = {}
        for line in out.splitlines():
            try:
                path_str, ln_no_str, _ = line.split(":", 2)
            except ValueError:
                continue
            seen.setdefault(path_str, set()).add(int(ln_no_str))
        for path_str, line_nos in seen.items():
            p = Path(path_str)
            text = await run_in_thread(read_text, p)
            snippets = []
            for ln_no in sorted(line_nos):
                ln = text.splitlines()[ln_no - 1] if 0 < ln_no <= len(text.splitlines()) else ""
                for m in pattern.finditer(ln):
                    snippets.append(MatchSnippet(line_no=ln_no, line=ln, match_start=m.start(), match_end=m.end()))
                    if len(snippets) >= 12:
                        break
            score = min(95.0, 40.0 + 2.0 * len(snippets))
            hits.append(SearchHit(title=p.stem, path=str(p), score=score, reason="content", snippets=snippets))
    else:
        paths = await run_in_thread(lambda: list(root.glob(MD_GLOB)))
        for p in paths:
            text = await run_in_thread(read_text, p)
            snippets = _collect_snippets_for_pattern(text, pattern, max_snips=12)
            if snippets:
                score = min(95.0, 40.0 + 2.0 * len(snippets))
                hits.append(SearchHit(title=p.stem, path=str(p), score=score, reason="content", snippets=snippets))

    # Limit and sort by score desc
    hits.sort(key=lambda h: (-h.score, h.title.lower()))
    return hits[:limit]


async def hybrid_search(root: str | Path, query: str, limit: int = 25) -> List[SearchHit]:
    """Fuse fuzzy title and content hits, dedupe by path, keep best score."""
    title_hits = await fuzzy_title_search(root, query, limit=limit * 2, threshold=50.0)
    content_hits = await grep_content(root, query, regex=False, case_sensitive=None, limit=limit * 4)
    by_path = {}
    for h in title_hits + content_hits:
        prev = by_path.get(h.path)
        if not prev or h.score > prev.score:
            by_path[h.path] = h
    merged = list(by_path.values())
    merged.sort(key=lambda h: (-h.score, h.title.lower()))
    return merged[:limit]