# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered automation platform called "ai-at-dscubed" that integrates with Discord, Notion, Gmail, and PostgreSQL. The project focuses on automating workflows for team management, scrum processes, and data processing.

## Architectural Concepts

### Workspace Structure

The project follows a modern **monorepo workspace pattern** using uv:

- **Apps** (`apps/`): Deployable applications and services
  - Each app is an independent, runnable service
  - Apps can depend on shared libraries and other apps
  - Examples: Discord bots, automation services, data processors

- **Libraries** (`libs/`): Shared code and utilities
  - **org_tools**: Reusable integrations and utilities (Notion, Gmail, PostgreSQL, etc.)
  - **org_types**: Shared type definitions and data models
  - **brain**: Data processing pipelines and ETL operations

- **External Dependencies**:
  - **llmgine**: Core LLM framework (separate repository, workspace dependency)

### Design Principles

**Modular Architecture**: Clear separation between applications, shared libraries, and external frameworks

**Workspace Dependencies**: Internal packages use `{ workspace = true }` for clean development workflow

**Integration Patterns**: 
- MCP (Model Context Protocol) servers for AI tool standardization
- Engine-based processing with command/event patterns
- Session management for stateful interactions

**Data Processing Pipeline**: Bronze (raw) → Silver (processed) data architecture

## Development Commands

### Package Management

This project uses `uv` for Python package management:
```bash
# Install dependencies
uv sync

# Add new dependency  
uv add <package-name>

# Run applications
uv run <app-name>
```

## Important Notes

- The project uses `uv` as the primary package manager with workspace dependencies
- MCP servers follow strict async/string return patterns for AI tool integration
- All internal packages use `{ workspace = true }` for editable development installs
- Python 3.13+ required
- Remember to use "uv run" instead of "python" 