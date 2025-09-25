"""
Cast Ops – Module Plan (for AAO Cast/MKD flat vaults)

Goals
-----
Provide a thin, async, function-calling friendly layer for:
  1) Finding context across a flat folder of Markdown (MKD) files
     - fuzzy title search, content grep (regex, ripgrep), hybrid ranking
  2) Reading and validating MKD structure & frontmatter
  3) Creating new MKD files from templates (frontmatter + footer sections)
  4) Editing existing files (search/replace; safe atomic writes; update 'last-updated')
  5) Renaming titles with global wikilink updates
  6) Comparing files or text (unified diff, frontmatter delta, section-by-section)

Key Concepts
------------
- MKD: Opinionated Markdown with:
  * YAML frontmatter at top (e.g., last-updated, category, type, base-version, tags)
  * body content (no leading H1; filename is the title)
  * Footer sentinel sections: '# =============', '# Dependencies', '# End'
  * Wikilinks: [[Title]], [[Title#Section]], [[Title|Alias]], typed refs like (requires)[[Title]]
  * Title/filename must follow MKD Title ID rules (forbidden: []:\/^|#*"<>)

- "Flat vault": We treat all *.md files under a root folder as a single plane of artifacts.
  Nested dirs are tolerated but not relied upon.

Workflows
---------
A. Retrieval:
   - `cast_search_titles_fuzzy()` → top-K fuzzy matches by filename title
   - `cast_grep()` → regex/literal search across file contents (ripgrep if present)
   - `cast_search_all()` → hybrid rank from titles + content matches
   - `cast_context_bundle()` → fetch canonical context chunks for top hits:
       * frontmatter + main body up to '# ============='
       * dependency list (resolved titles if available)
       * snippets around matches

B. Authoring/Editing:
   - `cast_create_note()` → create .md with normalized filename, YAML frontmatter,
                            footer sentinels, optional initial content and deps
   - `cast_edit_replace()` → search & replace within one file or glob across vault
                            (regex/literal), dry-run preview, unified diff per file,
                            auto-update 'last-updated'
   - `cast_rename_title()` → rename file + update all wikilinks vault-wide

C. Comparison/Validation:
   - `cast_compare_files()` / `cast_compare_text()` → unified diff (context lines)
   - `cast_compare_frontmatter()` → key-by-key changes
   - `cast_validate_note()` → MKD conformance checks with actionable issues

Design Principles
-----------------
- Async-first: all public APIs are async; blocking work runs in threads.
- Pure stdlib by default; optional accelerators (rapidfuzz, ripgrep, PyYAML) if present.
- JSON-safe returns for easy LLM tool calling.
- Atomic writes with .bak backup; never corrupt the vault.
- Non-destructive by default (dry-run previews).
- Small, composable modules; high-level `api.py` orchestrates.

Files & Responsibilities
------------------------
- const.py     → constants (forbidden characters for Title ID, file patterns)
- types.py     → dataclasses / typed dict builders for results
- utils.py     → async helpers, time stamps, atomic write, optional deps detection
- mkd.py       → parse/validate MKD frontmatter/body, wikilink parsing, templates
- indexer.py   → scan vault, collect NoteMeta (title/path/frontmatter/links)
- search.py    → fuzzy title search, grep/rg search, hybrid rank, snippet extract
- compare.py   → diff (files/text), frontmatter delta, section diffs
- edit.py      → create note, replace across files, rename & update wikilinks
- api.py       → public async functions for function calling (stable surface)
- __init__.py  → export the public API

Error Handling
--------------
Public APIs return: { "ok": bool, "data": ..., "error": str|None, "meta": {...} }
Errors never raise out of `api.py`; lower layers may raise, but API catches and formats.

Security/Conventions
--------------------
- We only touch files with extension '.md' under provided 'root'.
- We sanitize titles to conform to MKD Title ID Protocol (const.FORBIDDEN_CHARS).
- We update 'last-updated' on writes; timezone-naive "YYYY-MM-DD HH:mm".

Extensibility Hooks
-------------------
- Git integration (optional): can add commits after writes.
- Token budgets for context bundling (future).
- Caching index to disk (future).
"""