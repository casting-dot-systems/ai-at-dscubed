# Brain ORM

SQLAlchemy ORM-based data processing library for AI at D3, providing a modern, unified interface for managing Discord, Notion, and other data sources.

## Overview

Brain ORM is the next evolution of the brain data processing libraries, combining the functionality of `libs/brain` and `libs/brain_v2` with a modern SQLAlchemy ORM foundation. It provides:

- **Unified Data Models**: SQLAlchemy ORM models for members, components (channels/threads), messages, and reactions
- **High-Level API**: Simple async API for data operations and analysis
- **Migration Tools**: Utilities for transitioning from legacy data formats
- **Discord Integration**: Enhanced Discord data extraction and synchronization
- **Export Capabilities**: Export data to pandas DataFrames for analysis

## Installation

Add brain-core to your project dependencies:

```bash
uv add brain-core
```

Or install in development mode:

```bash
cd libs/brain-core
uv sync
```

## Quick Start

### 1. Database Setup

```python
from brain_orm import DatabaseManager, MigrationManager

# Setup database connection
db_manager = DatabaseManager("postgresql://user:pass@localhost/db")

# Initialize database schema
migration_manager = MigrationManager(db_manager)
await migration_manager.run_full_migration()
```

### 2. Basic Data Operations

```python
from brain_orm import BrainCoreAPI

api = BrainCoreAPI(db_manager)

# Create/find a member
member_id = await api.ensure_member_for_discord(
    org_id="your-org",
    discord_user_id="123456789",
    display_name="John Doe"
)

# Create a component (channel/thread)
component = await api.upsert_component(
    org_id="your-org",
    system="discord",
    component_id="channel-123",
    component_type="channel",
    name="general"
)

# Create a message
message = await api.upsert_message(
    org_id="your-org",
    system="discord",
    message_id="msg-456",
    component_id="channel-123",
    author_external_id="123456789",
    content="Hello, world!"
)
```

### 3. Discord Data Sync

```python
from brain_orm.extractors import DiscordOrmExtractor

# Set up Discord extractor
extractor = DiscordOrmExtractor(
    api=api,
    org_id="your-org",
    bot_token="your-bot-token",
    guild_id=your_guild_id
)

# Sync channels and messages
stats = await extractor.full_discord_sync()
print(f"Synced {stats['messages_synced']} messages")
```

### 4. Data Analysis

```python
# Get messages with filters
messages = await api.get_messages(
    component_id="channel-123",
    limit=100,
    include_reactions=True
)

# Export to DataFrame
df = await api.export_messages_to_dataframe(
    system="discord",
    start_date=datetime(2024, 1, 1)
)

# Get component statistics
stats = await api.get_component_stats(system="discord")
```

## CLI Usage

Brain ORM includes a command-line interface for common operations:

```bash
# Initialize database
uv run brain-core db init

# Check database status
uv run brain-core db status

# Sync Discord data
uv run brain-core sync discord --org-id your-org

# Export messages to CSV
uv run brain-core export messages -o messages.csv --system discord

# Show component statistics
uv run brain-core stats --system discord
```

## Data Models

### Core Models

- **Member**: Organization members with unified identity management
- **MemberIdentity**: External system identities (Discord, Notion, etc.)
- **Component**: Channels, threads, and other organizational units
- **Message**: Messages from various communication systems
- **Reaction**: Message reactions and engagement data

### Schema Structure

```
catalog.members              # Organization members
catalog.member_identities    # Identity mapping across systems

silver.components           # Channels, threads, etc.
silver.component_members    # Component membership
silver.messages            # All messages
silver.message_mentions    # Message mentions
silver.reactions           # Message reactions
```

## Migration from Legacy

If you're migrating from the original `libs/brain` or `libs/brain_v2`:

```python
from brain_orm.examples.migration_from_legacy import LegacyMigrator

migrator = LegacyMigrator(api)

# Migrate from CSV export
stats = await migrator.migrate_legacy_discord_data(
    csv_path="legacy_discord_data.csv",
    org_id="your-org"
)

# Validate migration
validation = await migrator.validate_migration("your-org")
```

## Configuration

Set these environment variables:

```bash
# Database connection
DATABASE_URL=postgresql://user:pass@localhost/dbname
ASYNC_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Discord integration (optional)
BOT_KEY=your_discord_bot_token
TEST_SERVER_ID=your_discord_guild_id
```

## Advanced Usage

### Custom Database Operations

```python
# Direct database access
async with db_manager.session_scope() as session:
    from brain_orm.models import Member, Message
    from sqlalchemy import select

    # Custom queries
    stmt = select(Member).where(Member.org_id == "your-org")
    members = await session.scalars(stmt)
```

### Batch Operations

```python
from brain_orm.extractors import DataFrameLoader

loader = DataFrameLoader(api)

# Load messages from DataFrame
count = await loader.load_messages_from_dataframe(
    df=your_dataframe,
    org_id="your-org",
    batch_size=1000
)
```

### Performance Tuning

```python
# Configure connection pooling
db_manager = DatabaseManager(
    database_url=url,
    echo=False,  # Disable SQL logging in production
)

# Use batch operations for large datasets
# Enable async operations for better performance
```

## Examples

See the `examples/` directory for detailed usage examples:

- `basic_usage.py`: Getting started with brain-core
- `migration_from_legacy.py`: Migrating from legacy brain libraries

## API Reference

### DatabaseManager

Manages database connections and sessions.

### BrainCoreAPI

High-level API for data operations.

Key methods:
- `ensure_member_for_discord()`: Create/find Discord members
- `upsert_component()`: Create/update components
- `upsert_message()`: Create/update messages
- `get_messages()`: Query messages with filters
- `export_messages_to_dataframe()`: Export to pandas

### DiscordOrmExtractor

Enhanced Discord data extraction with ORM integration.

### MigrationManager

Database schema and migration management.

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for API changes
4. Use async/await patterns consistently

## License

Part of the AI at D3 project workspace.