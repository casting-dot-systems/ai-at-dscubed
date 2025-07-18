# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered automation platform called "ai-at-dscubed" that integrates with Discord, Notion, Gmail, and PostgreSQL. The project focuses on automating workflows for team management, scrum processes, and data processing.

## Key Architecture

### Core Components

**Programs** (`/programs/`): Main applications that can be run independently
- **Discord Bot** (`/programs/discord/`): Main Discord bot with engine management and message processing
- **Scrum Checkup** (`/programs/scrum-checkup/`): Automated scrum process management and team checkups
- **Meeting Recorder Bot** (`/programs/meeting-recorder-bot/`): Bot for recording and managing meeting data
- **Darcy** (`/programs/darcy/`): Notion CRUD engines (v1, v2, v3) and fact processing

**Custom Tools** (`/custom_tools/`): Reusable utilities and integrations
- **Brain**: Notion and PostgreSQL integrations for data processing
- **Gmail**: Email client with OAuth2 authentication
- **Fact Checking**: Utilities for fact verification
- **MCP Servers**: Model Context Protocol servers for AI tool integration

**Brain** (`/brain/`): Data processing pipelines
- **Bronze**: Raw data extraction (Discord, Notion)
- **Silver**: Processed data with committees and checkups

## Development Commands

### Running Applications

```bash
# Run Discord bot in development mode (default)
python main.py

# Run Discord bot in production mode
python main.py --mode production

# Run with uv (recommended)
uv run programs/discord/bot.py

# Run scrum checkup bot
uv run programs/scrum-checkup/main.py
```

### Environment Setup

The project uses environment-specific configuration files:
- `.env.development` - Development environment
- `.env.production` - Production environment

The main.py script automatically copies the appropriate environment file to `.env` based on the `--mode` flag.

### Package Management

This project uses `uv` for Python package management:
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Run Python scripts
uv run <script.py>
```

## Key Integration Patterns

### MCP (Model Context Protocol) Servers

Located in `/custom_tools/mcp-servers/`, these provide standardized AI tool interfaces:
- All tools must be async functions returning strings
- Must use `@mcp.tool()` decorator
- Follow thin wrapper pattern around business logic
- Include comprehensive error handling

### Discord Bot Architecture

The Discord bot uses a modular architecture:
- **Engine Manager**: Coordinates different processing engines
- **Message Processor**: Handles incoming Discord messages
- **Session Manager**: Manages user sessions and state
- **Components**: Reusable UI components and utilities

### Notion Integration

Multiple Notion engines handle different use cases:
- **CRUD Engines**: v1, v2, v3 for different data operations
- **Brain Integration**: Automated data processing and extraction
- **Committee Management**: Team and committee data synchronization

## Dependencies

Core dependencies managed via `pyproject.toml`:
- **llmgine**: Custom LLM engine (local dependency)
- **notion**: Notion API client
- **Python 3.13+**: Required minimum version

## Testing

Individual components have test files:
- Gmail integration: `custom_tools/gmail/test_*.py`
- PostgreSQL: `custom_tools/brain/postgres/testing.py`

No unified test command found - test individual components as needed.

## Important Notes

- The project uses `uv` as the primary package manager
- Environment files are required for Discord bot operation
- MCP servers follow strict async/string return patterns
- All Notion integrations use custom engine architecture
- PostgreSQL integration is handled through the "brain" module