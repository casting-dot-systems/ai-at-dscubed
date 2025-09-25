from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from .const import MD_GLOB
from .mkd import split_frontmatter, extract_wikilinks
from .types import NoteMeta
from .utils import read_text, run_in_thread


class CastIndex:
    """Lightweight in-memory index of a Cast vault."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.notes_by_title: Dict[str, NoteMeta] = {}

    async def build(self) -> None:
        paths = await run_in_thread(lambda: list(self.root.glob(MD_GLOB)))
        metas: List[NoteMeta] = []
        for p in paths:
            if not p.is_file():
                continue
            try:
                text = await run_in_thread(read_text, p)
                fm, body = split_frontmatter(text)
                title = p.stem
                links = extract_wikilinks(body)
                st = p.stat()
                meta = NoteMeta(
                    title=title,
                    path=str(p),
                    size_bytes=st.st_size,
                    mtime=st.st_mtime,
                    frontmatter=fm or {},
                    tags=list(fm.get("tags", [])) if isinstance(fm.get("tags"), list) else [],
                    category=fm.get("category"),
                    type=fm.get("type"),
                    last_updated=fm.get("last-updated"),
                    links=links,
                )
                metas.append(meta)
            except Exception:
                continue
        self.notes_by_title = {m.title: m for m in metas}

    def get(self, title: str) -> NoteMeta | None:
        return self.notes_by_title.get(title)

    def titles(self) -> List[str]:
        return list(self.notes_by_title.keys())

    def all(self) -> List[NoteMeta]:
        return list(self.notes_by_title.values())