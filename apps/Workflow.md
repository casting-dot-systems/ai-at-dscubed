# AI-at-DSquared Component Workflow Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Analysis](#component-analysis)
3. [Interaction Patterns](#interaction-patterns)
4. [Example Workflow: Discord to Darcy Backend](#example-workflow-discord-to-darcy-backend)
5. [Message Flow Diagrams](#message-flow-diagrams)
6. [Key Design Patterns](#key-design-patterns)

## Architecture Overview

The AI-at-DSquared platform consists of four primary components that work together to provide AI-powered automation capabilities:

### 1. **llmgine** - Core LLM Framework
- **Purpose**: Pattern-driven framework for building production-grade, tool-augmented LLM applications
- **Key Features**: 
  - Async message bus for commands/events
  - Engine-based conversation logic
  - Tool registration and execution
  - Provider abstraction (OpenAI, Anthropic, Gemini)
  - Session management with automatic cleanup
  - Observability and metrics

### 2. **llmgineAPI** - WebSocket API Layer
- **Purpose**: FastAPI-based WebSocket server providing bidirectional communication
- **Key Features**:
  - WebSocket-only architecture for real-time communication
  - Request-response mapping with Future-based async operations
  - App-based session management
  - Extensible framework for custom backends
  - Connection registry and resource management

### 3. **discord_v2** - Frontend Client Implementation
- **Purpose**: Discord bot frontend that communicates with backend services
- **Key Features**:
  - WebSocket client for backend communication
  - Discord message processing and context enrichment
  - Session lifecycle management
  - Engine linking and message routing

### 4. **darcy_backend** - Backend Service Implementation
- **Purpose**: Specialized backend implementing llmgineAPI extensions
- **Key Features**:
  - Custom WebSocket handlers for engine operations
  - Multiple engine types (fact_processing, notion_crud)
  - Tool-augmented LLM processing with Notion/Gmail integration
  - Session-scoped engine management

## Component Analysis

### llmgine Core Framework

**Architecture Pattern**: Event-driven with message bus pattern
- **MessageBus**: Central communication hub using Commands (1:1) and Events (1:N)
- **Engines**: Stateful conversation processors with tool integration
- **Tools**: Declarative function registration with automatic schema generation
- **Providers**: Abstracted LLM backends with standardized interfaces
- **Sessions**: Scoped handler registration with automatic cleanup

**Key Files**:
- `src/llmgine/bus/bus.py` - Core message bus implementation
- `src/llmgine/llm/engine/engine.py` - Base engine class
- `src/llmgine/llm/tools/tool_manager.py` - Tool execution system

### llmgineAPI WebSocket Layer

**Architecture Pattern**: Extensible WebSocket-first API with bidirectional messaging
- **Connection Registry**: Thread-safe WebSocket connection tracking
- **Handler System**: Pluggable message handlers with type safety
- **Future-based Responses**: Async request-response mapping
- **Resource Management**: Automatic cleanup on disconnect

**Key Files**:
- `src/llmgineAPI/main.py` - FastAPI app factory
- `src/llmgineAPI/websocket/handlers.py` - Core WebSocket handlers
- `src/llmgineAPI/core/extensibility.py` - Extension framework

### discord_v2 Frontend

**Architecture Pattern**: Component-based Discord bot with WebSocket backend communication
- **Bot**: Main Discord bot orchestrator
- **SessionManager**: Discord session lifecycle with backend coordination
- **MessageProcessor**: Context enrichment with user data and chat history
- **EngineManager**: Backend API communication and engine lifecycle
- **WebSocketAPIClient**: Persistent connection with message queuing

**Key Files**:
- `bot.py` - Main Discord bot assembly
- `api/client.py` - WebSocket client implementation
- `engine_manager.py` - Backend API coordination
- `session_manager.py` - Session lifecycle management

### darcy_backend Service

**Architecture Pattern**: Extensible backend service using llmgineAPI framework
- **Handlers**: Custom WebSocket message handlers for engine operations
- **Engines**: Specialized LLM engines with tool integration
- **Messages**: Type-safe WebSocket message definitions
- **Factory**: API configuration and handler registration

**Key Files**:
- `main.py` - API factory and server startup
- `handlers.py` - Custom WebSocket handlers
- `engines/notion_crud_engine_v3.py` - Main business logic engine
- `messages.py` - WebSocket message schemas

## Interaction Patterns

### 1. WebSocket Communication Pattern
All components use WebSocket connections for real-time, bidirectional communication:

```
Frontend (discord_v2) <--WebSocket--> Backend (darcy_backend)
                                          |
                                     llmgineAPI
                                          |
                                       llmgine
```

### 2. Message Bus Pattern (Internal to llmgine)
Within engines and llmgine components, all communication uses the async message bus:

```
Engine --Command--> MessageBus --Event--> Multiple Listeners
```

### 3. Session Scoping
Sessions provide resource isolation and automatic cleanup:
- **Frontend**: Discord user sessions
- **Backend**: API app sessions  
- **Engine**: llmgine session scoping

### 4. Tool Registration and Execution
Tools are registered declaratively and executed through the tool manager:

```
Python Function --Register--> ToolManager --Execute--> LLM Tool Calls
```

## Example Workflow: Discord to Darcy Backend

### Scenario: User mentions bot in Discord with a task request

#### Phase 1: Discord Message Reception
1. **User Action**: User mentions @bot with message "Create a task for reviewing documents"
2. **Discord Bot (bot.py:on_message)**:
   - Validates message (not from bot, mentions bot)
   - Calls `MessageProcessor.process_mention()`

#### Phase 2: Message Processing and Session Creation
3. **MessageProcessor.process_mention()**:
   - Creates/retrieves session via `SessionManager.use_session()`
   - Enriches message with:
     - User mentions and Notion IDs
     - Author payload with facts/info
     - Chat history (last 20 messages)
     - Reply context if applicable

4. **SessionManager.use_session()**:
   - Generates session ID if new user
   - Creates backend session via `api_client.use_websocket("create_session")`
   - Updates Discord session status

#### Phase 3: Backend Session Creation
5. **WebSocket Client (api/client.py)**:
   - Sends `create_session` message to darcy_backend
   - Waits for `create_session_res` response
   - Returns session_id to session manager

6. **Darcy Backend (handlers.py)**:
   - Creates new session via llmgineAPI framework
   - Returns session_id in response

#### Phase 4: Engine Linking
7. **EngineManager.process_user_message()**:
   - Checks if engine is linked for session
   - If not, calls `link_engine()` with default type "notion_crud"

8. **Engine Linking Process**:
   - **Frontend**: Sends `link_engine` WebSocket message
   - **Backend**: `LinkEngineHandler.handle()` receives request
   - Creates `NotionCRUDEngineV3` instance
   - Initializes engine (registers tools: get_active_projects, create_task, etc.)
   - Registers engine with `EngineService`
   - Returns engine_id

#### Phase 5: Message Processing
9. **Message Execution**:
   - **Frontend**: Sends `use_engine` WebSocket message with enriched prompt
   - **Backend**: `UseEngineHandler.handle()` receives request
   - Retrieves registered engine for session
   - Calls `engine.execute(prompt)`

#### Phase 6: LLM Processing (Within NotionCRUDEngineV3)
10. **Engine.execute() → handle_prompt_command()**:
    - Adds user message to chat history
    - Enters tool execution loop:
      - Gets conversation context
      - Retrieves available tools
      - Calls LLM (GPT-4.1-mini) with context and tools
      - Processes tool calls if present
      - Executes tools (e.g., `get_active_projects`, `create_task`)
      - Adds tool results to context
      - Continues until no more tool calls
    - Returns final response

#### Phase 7: Tool Execution Example (With Bidirectional Confirmation)
11. **Tool Call: create_task**:
    - Engine parses LLM tool call arguments
    - Engine calls `handle_confirmation_command()` which uses WebSocket to request confirmation
    - Backend sends server-initiated confirmation request to frontend via WebSocket
    - Frontend receives confirmation request and shows YesNoView in the original Discord channel
    - User clicks Yes/No, response sent back to backend via WebSocket
    - Engine receives confirmation result and proceeds/aborts accordingly
    - If confirmed, executes `create_task()` function
    - Stores result in conversation context
    - Continues LLM loop

#### Phase 8: Response Delivery
12. **Response Flow**:
    - Engine returns final response to handler
    - Handler sends `use_engine_res` WebSocket message
    - Frontend receives response
    - Discord bot sends reply to user
    - Session status updated to "idle"

## Message Flow Diagrams

### WebSocket Message Flow
```
Discord User -> Discord Bot -> WebSocket Client -> darcy_backend -> llmgineAPI -> llmgine Engine
     ^                                                                                    |
     |                                            WebSocket Response                     |
     +------------ Discord Reply <-------------- use_engine_res <--------------------+
```

### Internal Engine Message Flow (llmgine)
```
Engine.execute() -> MessageBus.execute(Command) -> CommandHandler -> MessageBus.publish(Event) -> EventListeners
```

### Session Lifecycle
```
1. Discord Message -> 2. Create Session -> 3. Link Engine -> 4. Process Message -> 5. Return Response
      |                      |                   |                |                    |
   [Discord]           [API Session]       [Engine Created]   [LLM + Tools]      [Discord Reply]
```

## Key Design Patterns

### 1. **Layered Architecture**
- **Presentation**: Discord bot interface
- **Communication**: WebSocket API layer  
- **Business Logic**: llmgine engines with tools
- **Data**: Notion/Gmail/PostgreSQL integrations

### 2. **Event-Driven Architecture**
- Async message bus for loose coupling
- Commands for operations, Events for notifications
- Session-scoped handlers with automatic cleanup

### 3. **Plugin Architecture**
- Tools registered as Python functions
- Engines as pluggable conversation processors  
- Providers as interchangeable LLM backends

### 4. **Resource Management**
- Automatic session cleanup on disconnect
- Connection registry with health monitoring
- Future-based async operations with timeouts

### 5. **Type Safety**
- Pydantic models for all message types
- Full type hints throughout codebase
- Runtime validation at API boundaries

This architecture provides a scalable, maintainable foundation for building complex AI-powered automation systems with real-time communication, tool integration, and robust session management.

## Bidirectional WebSocket Confirmations

### Overview
The system implements bidirectional WebSocket communication that allows the backend to request real-time user confirmations through Discord. This feature enables the AI engine to seek user approval before executing sensitive operations like creating tasks or updating records.

### Architecture Components

#### Backend Components (darcy_backend)
1. **Enhanced Message Schemas** (`messages.py`):
   - `UseEngineRequest` includes `channel_id` field
   - `ConfirmationServerRequest` for server-initiated confirmations
   - `ConfirmationServerResponse` for user responses

2. **Engine Modifications** (`engines/notion_crud_engine_v3.py`):
   - `handle_confirmation_command()` uses WebSocket messaging API
   - Sends server-initiated confirmation requests with channel context
   - Waits for user response with timeout handling

3. **Handler Updates** (`handlers.py`):
   - `UseEngineHandler` extracts and passes `channel_id` to engines
   - Links messaging API to engines for bidirectional communication

#### Frontend Components (discord_v2)
1. **WebSocket Client** (`api/client.py`):
   - Server message handler registration system
   - `_handle_server_request()` method for processing server-initiated messages
   - `send_server_response()` method for sending responses back

2. **Session Manager** (`session_manager.py`):
   - `_handle_confirmation_request()` method bridges WebSocket to Discord UI
   - Uses existing `YesNoView` components for user interaction
   - Sends confirmations to the correct Discord channel

3. **Engine Manager** (`engine_manager.py`):
   - Passes `channel_id` in `use_engine` messages
   - Maintains channel context throughout the request flow

### Message Flow

#### Confirmation Request Flow
```
1. Engine needs confirmation → 2. handle_confirmation_command() → 3. WebSocket server request
     ↓                                                                        ↓
4. Frontend receives → 5. Show YesNoView in Discord → 6. User clicks Yes/No → 7. WebSocket response
     ↓                                                                        ↓
8. Engine receives result → 9. Continue/abort tool execution → 10. Final response to user
```

#### WebSocket Message Structure
**Server-Initiated Confirmation Request:**
```json
{
  "type": "server_request",
  "message_id": "unique-uuid",
  "server_initiated": true,
  "data": {
    "request_type": "confirmation",
    "prompt": "Creating task {...}",
    "session_id": "session-123",
    "channel_id": "discord-channel-id"
  }
}
```

**Client Response:**
```json
{
  "type": "server_response",
  "message_id": "same-uuid",
  "data": {
    "response_type": "confirmation",
    "confirmed": true,
    "session_id": "session-123"
  }
}
```

### Key Features
- **Channel-Aware**: Confirmations appear in the same Discord channel as the original request
- **Real-time**: Immediate user interaction without polling or delays
- **Timeout Handling**: Automatic denial if user doesn't respond within 30 seconds
- **Error Recovery**: Graceful fallback to denial on connection issues
- **UI Integration**: Reuses existing Discord `YesNoView` components

### Example Workflow
1. User: "Create a task for code review"
2. Engine processes request, needs confirmation for `create_task` tool
3. Backend sends WebSocket confirmation request with channel_id
4. Discord bot shows YesNoView in the original channel: "⚠️ **Confirmation Required**: Creating task {...}"
5. User clicks "Yes" → WebSocket response sent to backend
6. Engine receives confirmation, executes `create_task()` function
7. Final response: "Task created successfully!"

## Implementation Changes Table

| File | Main Changes | Date | Comments |
|------|-------------|------|----------|
| `darcy_backend/messages.py` | Added `channel_id` to `UseEngineRequest`, created `ConfirmationServerRequest/Response` message types | 2025-01-24 | Enables channel-aware server-initiated confirmations |
| `darcy_backend/engines/notion_crud_engine_v3.py` | Modified `handle_confirmation_command()` to use WebSocket messaging API, added `set_channel_id()` and `set_app_id()` methods | 2025-01-24 | Core bidirectional confirmation logic |
| `darcy_backend/handlers.py` | Updated `UseEngineHandler` to extract `channel_id` and pass messaging API to engines | 2025-01-24 | Links WebSocket context to engine operations |
| `darcy_backend/main.py` | Added messaging API access to handlers through app state | 2025-01-24 | Enables handlers to access bidirectional messaging |
| `discord_v2/api/client.py` | Added server message handling, `_handle_server_request()` method, and response sending capabilities | 2025-01-24 | Core frontend WebSocket bidirectional support |
| `discord_v2/session_manager.py` | Added `_handle_confirmation_request()` method that bridges WebSocket to Discord UI | 2025-01-24 | Connects server confirmations to Discord interface |
| `discord_v2/engine_manager.py` | Modified `process_user_message()` to include `channel_id` parameter | 2025-01-24 | Passes channel context through the request pipeline |
| `discord_v2/bot.py` | Updated bot to pass `message.channel.id` to engine manager | 2025-01-24 | Captures channel context from Discord messages |