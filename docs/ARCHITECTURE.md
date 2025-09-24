# AI-at-DScubed System Architecture

**AI-powered automation platform for the Data Science Student Society (DSCubed) at the University of Melbourne**

## Table of Contents
- [Overview](#overview)
- [Architectural Principles](#architectural-principles)
- [System Components](#system-components)
- [Shared Libraries](#shared-libraries)
- [External Integrations](#external-integrations)
- [Data Architecture](#data-architecture)
- [Development Workflow](#development-workflow)
- [Security & Authentication](#security--authentication)
- [Observability](#observability)

## Overview

The ai-at-dscubed platform is a sophisticated automation system that integrates Discord, Notion, Gmail, and PostgreSQL to streamline team management, scrum processes, and data operations. Built on the `llmgine` LLM framework, it follows modern Python development practices with a monorepo workspace structure.

### Key Capabilities
- **Discord Bot Management**: Multi-bot system for team interaction and automation
- **Notion Integration**: Automated task and project management
- **Scrum Automation**: Intelligent scrum checkups and progress tracking  
- **Data Processing**: Bronze-Silver-Gold data pipeline architecture
- **AI Tool Standardization**: MCP (Model Context Protocol) integration

## Architectural Principles

### Modern Monorepo Structure
```
ai-at-dscubed/
├── apps/           # Deployable applications and services
├── libs/           # Shared libraries and utilities
├── llmgine/        # External LLM framework (workspace dependency)
└── pyproject.toml  # Root workspace configuration
```

### Design Patterns
- **Event-Driven Architecture**: Message bus for inter-component communication
- **Workspace Dependencies**: Clean separation with `{ workspace = true }`
- **Type Safety**: NewType definitions for platform-specific identifiers
- **Engine Pattern**: Pluggable conversation logic via `llmgine`
- **Singleton Clients**: Resource management for external API connections

## System Components

### Applications (`apps/`)

#### **Darcy** - Core Automation Engine
- **Purpose**: Notion CRUD operations with fact processing
- **Components**:
  - `fact_processing_engine.py`: Intelligent fact validation and management
  - `notion_crud_engine_v3.py`: Sophisticated Notion interface with user confirmation
  - `main.py`: Discord bot launcher (entry point)
- **Integration**: OpenAI GPT-4.1 Mini with custom tool system

#### **Discord Bot** - Team Interaction
- **Purpose**: AI assistant "Daryl" for DSCubed team management
- **Components**:
  - `bot.py`: Main bot controller with personality framework
  - `message_processor.py`: Enrichment pipeline for user context
  - `session_manager.py`: Stateful interaction management
  - `engine_manager.py`: LLM tool and command registration
- **Features**: User mention processing, chat history, reply context

#### **Discord Bot V2** - Enhanced Integration
- **Purpose**: WebSocket API integration with slash commands
- **Enhancements**:
  - `/connect` slash command for session creation
  - Real-time WebSocket communication
  - Interactive engine selection UI
  - API service layer for notifications
- **Architecture**: Separation of API concerns from bot logic

#### **Scrum Checkup** - Process Automation
- **Purpose**: Automated scrum management with intelligent scheduling
- **Components**:
  - `scrum_checkup_engine.py`: Interactive conversation management
  - `scrum_update_engine.py`: Post-conversation processing
  - `main.py`: Event-driven coordination
- **Features**: Natural conversation termination, task status updates, scheduling

#### **Meeting Recorder Bot** - Voice Capture
- **Purpose**: Meeting transcription and documentation
- **Implementation**: 
  - Custom `VoiceRecord` class extending Discord voice client
  - Per-user audio file creation (PCM format)
  - Real-time packet processing

## Shared Libraries

### **org_tools** - Integration Utilities
Primary integration layer providing reusable tools for external services.

#### **brain/** - Data Processing
- **notion/**: High-level Notion CRUD operations with task management
- **postgres/**: Database operations with SCD2 temporal modeling
- Functions: User facts, committee management, personal checkups

#### **gmail/** - Email Integration
- **gmail_client.py**: Google Gmail API wrapper
- Features: OAuth2 flow, thread-aware replies, HTML/text support

#### **mcp_servers/** - AI Tool Standardization
- **notion/tools.py**: Model Context Protocol server for Notion
- Pattern: FastMCP framework with async tool definitions

#### **notion/raw/** - Low-Level API Client
- **client.py**: Direct Notion API wrapper with comprehensive type safety
- Features: Property parsing, enum-based status, error-safe extraction

#### **fact_checking/** - User Data Management
- **functions.py**: CRUD operations for personal facts
- Integration: LLMgine message bus for approval workflows

### **org_types** - Type Safety
Centralized type definitions using NewType pattern for platform-specific identifiers.

```python
# Discord Types
DiscordChannelID = NewType("DiscordChannelID", str)
DiscordUserID = NewType("DiscordUserID", str)

# Notion Types  
NotionUserID = NewType("NotionUserID", str)
NotionTaskID = NewType("NotionTaskID", str)
```

### **brain** - Data Processing
Data pipeline implementation following Bronze-Silver-Gold architecture.

#### **bronze/** - Raw Data Extraction
- **pipelines/**: ETL implementations for Discord and Notion
- **extractors/**: Data fetching with pagination and type safety
- **DDL/**: Database schema definitions

#### **silver/** - Processed Data
- **DDL/**: Enhanced schemas with temporal modeling
- **DML/**: Data transformation queries

## External Integrations

### Service Integrations

#### **Discord API**
- **Library**: `discord.py>=2.3.2`
- **Pattern**: Event-driven bot with command handling
- **Authentication**: Bot token via `BOT_KEY` environment variable
- **Features**: Message intents, session management, slash commands

#### **Notion API**
- **Library**: `notion-client>=2.3.0`
- **Pattern**: Singleton client with comprehensive CRUD
- **Authentication**: API token via `NOTION_TOKEN`
- **Architecture**: Raw client wrapper with type-safe models

#### **Gmail API**
- **Libraries**: Google API client suite (`google-api-python-client>=2.169.0`)
- **Authentication**: OAuth2 with credential caching
- **Features**: Send/reply with threading, content processing

#### **PostgreSQL**
- **Libraries**: `psycopg2-binary>=2.9.10`, `sqlalchemy>=2.0.40`
- **Pattern**: Connection singleton with raw SQL
- **Authentication**: `DATABASE_URL` environment variable

### LLM Framework (`llmgine`)

#### **Core Dependencies**
- **Anthropic**: `anthropic>=0.50.0` (Claude models)
- **OpenAI**: Via `litellm>=1.63.12`
- **MCP**: `mcp>=1.10.1` (Model Context Protocol)

#### **Framework Components**
- **Message Bus**: Async command/event coordination
- **Engine Pattern**: Base abstractions for conversation logic
- **Tool Management**: Dynamic registration with multi-provider support
- **Observability**: Event tracking with JSONL logging

## Data Architecture

### Bronze-Silver-Gold Pipeline
- **Bronze**: Raw data extraction from Discord and Notion APIs
- **Silver**: Processed data with type validation and enrichment
- **Gold**: Analytics-ready data (planned)

### Database Patterns
- **SCD2 Modeling**: Slowly Changing Dimensions for historical tracking
- **Event Sourcing**: Integration with LLMgine event bus
- **User Management**: Discord-Notion ID mapping with fact storage

### Data Flow
```
External APIs → Bronze (Raw) → Silver (Processed) → Applications
    ↓              ↓              ↓
Discord API    ETL Pipelines   Type Safety
Notion API     Error Handling  Validation
Gmail API      Pagination      Enrichment
```

## Development Workflow

### Package Management
- **Tool**: `uv` (modern Python package manager)
- **Pattern**: Workspace dependencies with editable installs
- **Requirements**: Python 3.13+

### Key Commands
```bash
# Install dependencies
uv sync

# Run applications  
uv run <app-name>

# Add workspace dependency
uv add --dev <package> --workspace
```

### Development Stack
- **Testing**: `pytest>=8.3.5` with async support
- **Code Quality**: `ruff>=0.9.2`, `mypy>=0.991`, `pre-commit>=2.20.0`
- **CLI Tools**: `rich>=13.9.4`, `textual>=2.1.2`

## Security & Authentication

### Authentication Patterns
- **Environment Variables**: API tokens and connection strings
- **OAuth2**: Gmail integration with token refresh
- **Local Files**: Gmail OAuth credentials (`client_secret.json`, `token.json`)

### Security Features
- **Type Safety**: Comprehensive validation with Pydantic
- **Connection Pooling**: SQLAlchemy engine management
- **Singleton Patterns**: Resource management for API clients
- **Error Handling**: Graceful degradation with descriptive messages

### Required Environment Variables
```bash
NOTION_TOKEN=<notion_api_token>
BOT_KEY=<discord_bot_token>
BOT_ID=<discord_bot_id>
DATABASE_URL=<postgresql_connection_string>
```

## Observability

### Event Architecture
- **Message Bus**: All component communication flows through central bus
- **Event Types**: Commands (1:1), Events (1:N), Scheduled Events
- **Persistence**: Database storage for scheduled and recurring events

### Monitoring Tools
- **Event Logging**: Structured JSONL format with timestamps
- **CLI Tools**: Log search, statistics, trace visualization
- **GUI Dashboard**: React-based real-time event viewer
- **Session Tracking**: Automatic cleanup with status indicators

### Event Flow
```
User Input → Discord Bot → Message Bus → Engine → Tools → External APIs
     ↓            ↓           ↓          ↓       ↓
  Event Log   Session Mgmt  Commands   Results  Status
```

## Future Considerations

### Scalability
- **Horizontal Scaling**: Message bus supports multi-instance deployment
- **Database Sharding**: Prepared for user-based partitioning
- **Caching**: Redis integration for session and API response caching

### Enhancement Areas
- **Retry Mechanisms**: More sophisticated error handling and backoff
- **Configuration Management**: Structured validation and environment separation
- **Secrets Management**: Integration with cloud secret managers
- **Monitoring**: Metrics and alerting for production deployments

---

*This architecture supports the platform's mission of automating team workflows while maintaining clean separation of concerns, type safety, and comprehensive observability throughout the system.*