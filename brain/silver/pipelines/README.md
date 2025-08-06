# Silver Data Pipelines

This directory contains the silver layer data transformation pipelines that convert bronze Discord data into a structured, analysis-ready format.

## Overview

The silver layer uses a new schema with tables prefixed `internal_msg_*` that represent:

- **Components**: Discord channels, forums, threads (was `internal_text_channel_meta`)
- **Messages**: All message content (was `internal_text_channel_messages`) 
- **Members**: Who has access to which components
- **Conversations**: Grouped related messages
- **Conversation Members**: Who participated in conversations

## Quick Start

### Run All Pipelines (Recommended)
```bash
cd brain/silver/pipelines
python orchestrator.py
```

### Run Individual Pipelines
```bash
# 1. Component metadata (channels/forums)
python populate_channel_meta_simple.py

# 2. Component member relationships (optional)
python populate_component_members.py

# 3. Message content
python populate_channel_messages_simple.py
```

## Pipeline Dependencies

```
bronze.discord_relevant_channels (ingest=TRUE)
└── internal_msg_component
    └── internal_msg_members (optional)
    
bronze.discord_chats
├── silver.committee (for member_id lookup)
└── internal_msg_message
```

## Table Schema

### internal_msg_component
- **component_id**: Unique identifier (maps to Discord channel_id)
- **platform_name**: Always "Discord" 
- **component_type**: "discord_channel", "discord_thread", etc.
- **parent_component_id**: Parent category/channel ID
- **component_name**: Display name
- **created_at**: When component was created
- **section_name**: Category name (if in category)

### internal_msg_message  
- **message_id**: Auto-generated primary key
- **member_id**: Committee member ID (positive) or negative Discord user ID (non-committee)
- **component_id**: Which component the message belongs to
- **msg_txt**: Message content
- **msg_type**: "channel_message" or "thread_message"
- **sent_at**: When message was sent
- **edited_at**: When message was last edited

### internal_msg_members
- **member_id**: Committee member ID
- **component_id**: Which component they have access to  
- **role**: Their role in that component
- **joined_at**: When they joined (if available)
- **left_at**: When they left (if available)

## Data Flow

1. **Bronze Layer**: Raw Discord API data in `bronze.discord_chats` and `bronze.discord_relevant_channels`

2. **Silver Layer**: Cleaned, structured data with:
   - Consistent naming (`component_id` instead of `channel_id`)
   - Member ID mapping (committee members get positive IDs, non-committee get negative Discord IDs)
   - Message type classification
   - Proper foreign key relationships

## Configuration

Set these environment variables in your `.env` file:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

## Troubleshooting

### "No channels found with ingest=TRUE"
- Ensure `bronze.discord_relevant_channels` has records with `ingest=TRUE`
- Run the bronze pipeline first

### "No committee members found"
- The `silver.committee` table is used for member ID mapping
- Non-committee members will still be processed with negative IDs

### Pipeline fails with table not found
- DDL files are automatically executed to create tables
- Check database permissions and connection

## Migration from Old Schema

If migrating from the old `internal_text_channel_*` tables:

1. The new pipelines will create `internal_msg_*` tables
2. Old tables are not automatically dropped
3. Update any queries/reports to use the new table names
4. Consider running both schemas in parallel during transition

## Extending the Pipelines

To add new transformations:

1. Create new DDL files in `../src/DDL/`
2. Add pipeline scripts following the existing patterns
3. Update `orchestrator.py` to include your new pipeline
4. Test with small data sets first 