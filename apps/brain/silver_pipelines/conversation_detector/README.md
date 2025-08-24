# Conversation Detector Engine

This engine detects conversations in text channel messages using LLM analysis and stores the results in the database.

## Overview

The Conversation Detector Engine processes messages from `silver.internal_text_channel_messages` and:

1. **Detects Conversation Boundaries**: Uses LLM to identify distinct conversations based on topic changes and conversation flow
2. **Identifies Participants**: Determines which committee members participated in each conversation
3. **Creates Summaries**: Generates concise summaries for each conversation
4. **Stores Results**: Inserts data into three database tables:
   - `silver.internal_text_channel_convos` - Conversation summaries
   - `silver.internal_text_chnl_convo_members` - Conversation participants
   - `silver.internal_text_chnl_msg_convo_member` - Message-conversation links

## Features

- **Incremental Processing**: Only processes new messages (not already linked to conversations)
- **Channel-by-Channel Processing**: Processes one channel at a time as selected by user
- **LLM-Powered Detection**: Uses GPT-4.1 to intelligently detect conversation boundaries
- **Error Handling**: Graceful fallback when LLM parsing fails
- **Database Integration**: Full integration with existing database schema

## Usage

### Prerequisites

1. Ensure the database tables exist:
   - `silver.internal_text_channel_messages` (source data)
   - `silver.internal_text_channel_convos` (conversations)
   - `silver.internal_text_chnl_convo_members` (participants)
   - `silver.internal_text_chnl_msg_convo_member` (message links)
   - `silver.committee` (member information)

2. Set up environment variables:
   - `DATABASE_URL` - PostgreSQL connection string
   - `OPENAI_API_KEY` - OpenAI API key

### Running the Engine

```bash
cd apps/brain/silver_pipelines/conversation_detector
python conversation_detector.py
```

The engine will:
1. Show available channels with message counts
2. Prompt you to select a channel to process
3. Process new messages in that channel
4. Display results summary

### Example Output

```
Conversation Detector Engine
========================================
This engine will detect conversations in text channel messages using LLM.

Available channels:
Channel 1: 55 messages
Channel 3: 36 messages

Enter channel ID to process: 1

===== CONVERSATION DETECTION RESULTS =====

Conversations detected: 5
Messages processed: 55
Members identified: 8
```

## Database Schema

### Input Table
- `silver.internal_text_channel_messages` - Source messages with columns:
  - `message_id` (BIGINT)
  - `member_id` (BIGINT)
  - `channel_id` (BIGINT)
  - `message` (TEXT)
  - `date_created` (TIMESTAMP)

### Output Tables

#### `silver.internal_text_channel_convos`
- `convo_id` (SERIAL PRIMARY KEY)
- `convo_summary` (TEXT)
- `ingestion_timestamp` (TIMESTAMP)

#### `silver.internal_text_chnl_convo_members`
- `convo_id` (INTEGER, FK to convos)
- `member_id` (INTEGER, FK to committee)
- `ingestion_timestamp` (TIMESTAMP)
- PRIMARY KEY (convo_id, member_id)

#### `silver.internal_text_chnl_msg_convo_member`
- `message_id` (BIGINT)
- `member_id` (INTEGER, FK to committee)
- `convo_id` (INTEGER, FK to convos)
- `ingestion_timestamp` (TIMESTAMP)
- PRIMARY KEY (message_id, convo_id)

## LLM Processing

The engine uses a sophisticated prompt that instructs the LLM to:

1. **Analyze Message Flow**: Detect conversation boundaries based on topic changes
2. **Identify Participants**: Determine which committee members were involved
3. **Generate Summaries**: Create informative conversation summaries

The LLM returns structured JSON with conversation details, which is then parsed and stored in the database.

## Error Handling

- **LLM Parsing Errors**: Falls back to creating a single conversation with all messages
- **Database Errors**: Continues processing other conversations if one fails
- **Invalid Data**: Validates member IDs against committee table before insertion

## Dependencies

- `sqlalchemy` - Database ORM
- `asyncpg` - PostgreSQL async driver
- `llmgine` - LLM framework
- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management 