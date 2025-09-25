from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class MatchSnippet:
    line_no: int
    line: str
    match_start: int
    match_end: int


@dataclass
class SearchHit:
    title: str
    path: str
    score: float
    reason: str  # "title" | "content" | "hybrid"
    snippets: List[MatchSnippet]


@dataclass
class NoteMeta:
    title: str
    path: str
    size_bytes: int
    mtime: float
    frontmatter: Dict[str, Any]
    tags: List[str]
    category: Optional[str]
    type: Optional[str]
    last_updated: Optional[str]
    links: List[str]  # [[wikilinks]] targets (titles only, no sections)


@dataclass
class DiffResult:
    a_label: str
    b_label: str
    diff_unified: str


def to_json_safe(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    return obj