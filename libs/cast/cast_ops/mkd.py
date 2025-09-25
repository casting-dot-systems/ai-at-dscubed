from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from .const import YAML_FM_DELIM, FOOTER_SPLIT_TITLE, DEPS_TITLE, END_TITLE, FORBIDDEN_CHARS
from .utils import yaml_load, now_timestamp_str, read_text

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SECTION_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def split_frontmatter(raw: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter dict and return (fm, body)."""
    raw = raw.lstrip("\ufeff")  # strip BOM if present
    if not raw.startswith(YAML_FM_DELIM + "\n"):
        return {}, raw
    end = raw.find("\n" + YAML_FM_DELIM + "\n", len(YAML_FM_DELIM) + 1)
    if end == -1:
        # malformed, treat as no frontmatter
        return {}, raw
    yaml_text = raw[len(YAML_FM_DELIM) + 1 : end]
    body = raw[end + len(YAML_FM_DELIM) + 2 :]
    fm = yaml_load(yaml_text)
    return fm, body


def extract_wikilinks(text: str) -> List[str]:
    return list({m.group(1).strip() for m in WIKILINK_PATTERN.finditer(text)})


def find_dependencies_section(text: str) -> Tuple[int, int]:
    """Return (start_index, end_index) of the Dependencies section body (list items)."""
    m = re.search(r"^#\s*Dependencies\s*$", text, flags=re.MULTILINE)
    if not m:
        return -1, -1
    start = m.end()
    # until next heading
    m2 = SECTION_HEADING_PATTERN.search(text, pos=start)
    end = m2.start() if m2 else len(text)
    return start, end


def parse_dependencies(text: str) -> List[str]:
    start, end = find_dependencies_section(text)
    if start == -1:
        return []
    section = text[start:end]
    links = extract_wikilinks(section)
    return links


def ensure_footer_blocks(body: str) -> str:
    """Ensure footer sentinel sections exist in proper order."""
    parts = body
    if FOOTER_SPLIT_TITLE not in parts:
        parts += f"\n\n{FOOTER_SPLIT_TITLE}\n\n"
    if re.search(r"^#\s*Dependencies\s*$", parts, flags=re.MULTILINE) is None:
        parts += f"\n{DEPS_TITLE}\n\n"
    if re.search(r"^#\s*End\s*$", parts, flags=re.MULTILINE) is None:
        parts += f"\n{END_TITLE}\n"
    return parts


def normalize_title_id(title: str) -> str:
    """Remove forbidden characters; collapse whitespace; trim."""
    cleaned = "".join(ch if ch not in FORBIDDEN_CHARS else " " for ch in title)
    # collapse whitespace and dots around
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip(".")
    return cleaned


def make_frontmatter(base: Dict) -> str:
    # Keep order readable; minimal YAML generation
    keys = ["last-updated", "tags", "category", "type", "base-version"]
    lines = ["---"]
    for k in keys:
        v = base.get(k)
        if v is None:
            continue
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"- {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def build_new_note_text(frontmatter: Dict, content: str, dependencies: List[str] | None) -> str:
    fm = dict(frontmatter)
    fm.setdefault("last-updated", now_timestamp_str())
    fm_text = make_frontmatter(fm)
    body = content.rstrip() + "\n\n"
    body = ensure_footer_blocks(body)
    if dependencies:
        # Insert after '# Dependencies'
        pattern = re.compile(r"^#\s*Dependencies\s*$", flags=re.MULTILINE)
        m = pattern.search(body)
        if m:
            insert_at = m.end()
            dep_lines = "".join(f"\n- [[{t}]]" for t in dependencies)
            body = body[:insert_at] + dep_lines + body[insert_at:]
    return fm_text + body


def read_note(path: Path) -> Tuple[Dict, str, str]:
    raw = read_text(path)
    fm, body = split_frontmatter(raw)
    return fm, body, raw