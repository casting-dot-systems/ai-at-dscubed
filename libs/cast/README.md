# Cast Ops - MKD Vault Operations

Cast Ops is an async, function-calling friendly Python library for managing flat folders of MKD/Markdown files (Cast vaults). It provides comprehensive functionality for finding context, reading/writing files, and editing with safety guarantees.

## Features

- **Search Operations**: Fuzzy title search, content grep (with ripgrep support), hybrid ranking
- **File Operations**: Read, create, edit with atomic writes and backup
- **MKD Support**: Full support for MKD format with YAML frontmatter and footer sections
- **Wikilink Management**: Parse and update wikilinks across the vault
- **Async-first**: All operations use asyncio for non-blocking I/O
- **Tool-friendly**: JSON-safe returns designed for LLM function calling

## Quick Start

```python
import asyncio
from cast_ops import (
    cast_search_titles_fuzzy,
    cast_grep,
    cast_create_note,
    cast_read_note,
    cast_context_bundle,
)

async def main():
    root = "/path/to/vault"

    # Search by title
    result = await cast_search_titles_fuzzy(root, "my note")

    # Search content
    result = await cast_grep(root, "important keywords")

    # Create a new note
    result = await cast_create_note(
        root,
        title="New Note",
        content="Some content",
        frontmatter={"category": "work"},
        dependencies=["Related Note"]
    )

    # Get context bundle for AI
    result = await cast_context_bundle(root, "project planning", top_k=5)

asyncio.run(main())
```

## API Functions

### Search Operations
- `cast_search_titles_fuzzy(root, query, limit=20, threshold=55.0)` - Fuzzy search by title
- `cast_grep(root, query, regex=False, case_sensitive=None, limit=2000)` - Content search
- `cast_search_all(root, query, limit=25)` - Hybrid title + content search
- `cast_context_bundle(root, query, strategy="hybrid", top_k=8)` - Get context for AI

### File Operations
- `cast_read_note(root, title_or_path)` - Read a single note
- `cast_create_note(root, title, content="", frontmatter=None, dependencies=None)` - Create new note
- `cast_edit_replace(root, find, replace, regex=False, dry_run=True)` - Search and replace
- `cast_rename_title(root, old_title, new_title, update_links=True)` - Rename with link updates

### Utility Operations
- `cast_build_index(root)` - Build in-memory index of vault
- `cast_validate_note(root, title_or_path)` - Check MKD format compliance
- `cast_compare_files(a_path, b_path, context_lines=3)` - File diff
- `cast_compare_frontmatter(a_path, b_path)` - Compare YAML frontmatter

## MKD Format

Cast Ops works with MKD (Markdown with structure) files:

```markdown
---
last-updated: 2025-01-15 10:30
category: project
type: note
tags:
- planning
- work
---

Main content goes here.

# =============

# Dependencies

- [[Related Note]]
- [[Another Dependency]]

# End
```

## Optional Dependencies

For enhanced performance, install optional accelerators:

```bash
pip install rapidfuzz pyyaml
```

- **rapidfuzz**: Faster fuzzy string matching
- **pyyaml**: More robust YAML parsing
- **ripgrep**: Much faster content search (auto-detected)

## Error Handling

All functions return structured results:

```python
{
    "ok": True,           # Success flag
    "data": {...},        # Result data
    "error": None,        # Error message if failed
    "meta": {...}         # Additional metadata
}
```

## Safety Features

- Atomic writes with backup files
- Dry-run previews for destructive operations
- Automatic `last-updated` timestamp management
- Non-destructive by default
- Input sanitization and validation

## Development

Run tests:

```bash
uv run python test_cast.py
```

The library is designed to be minimal with no hard dependencies, using only Python standard library with optional accelerators for performance.