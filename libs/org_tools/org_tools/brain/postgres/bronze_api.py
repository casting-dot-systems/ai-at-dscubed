from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from bronze_data_access import BronzeDataAccess
import os

app = FastAPI(title="Bronze Data API", description="Read-only access to bronze table data")

# Initialize data access
bronze_data = BronzeDataAccess()


class DiscordChat(BaseModel):
    chat_id: int
    channel_id: int
    channel_name: str
    thread_name: Optional[str]
    thread_id: Optional[int]
    message_id: int
    discord_username: str
    discord_user_id: int
    content: Optional[str]
    chat_created_at: str
    chat_edited_at: Optional[str]
    is_thread: bool
    ingestion_timestamp: str


class CommitteeMember(BaseModel):
    member_id: int
    name: str
    notion_id: Optional[str]
    discord_id: Optional[str]
    discord_dm_channel_id: Optional[int]
    ingestion_timestamp: str


@app.get("/")
async def root():
    return {"message": "Bronze Data API - Read-only access to bronze tables"}


@app.get("/discord/chats", response_model=List[DiscordChat])
async def get_discord_chats(
    channel_id: Optional[int] = Query(None, description="Filter by channel ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    days_back: Optional[int] = Query(None, description="Filter by messages from last N days"),
    limit: Optional[int] = Query(100, description="Limit number of results", le=1000)
):
    """Get Discord chat messages with optional filters."""
    try:
        chats = bronze_data.get_discord_chats(
            channel_id=channel_id,
            user_id=user_id,
            days_back=days_back,
            limit=limit
        )
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/discord/channels")
async def get_discord_channels(
    limit: Optional[int] = Query(100, description="Limit number of results", le=1000)
):
    """Get Discord channel metadata."""
    try:
        channels = bronze_data.get_discord_channels(limit=limit)
        return channels
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/committee/members", response_model=List[CommitteeMember])
async def get_committee_members():
    """Get committee member data."""
    try:
        members = bronze_data.get_committee_members()
        return members
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/discord/relevant-channels")
async def get_relevant_channels():
    """Get relevant Discord channels."""
    try:
        channels = bronze_data.get_relevant_channels()
        return channels
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema/{table_name}")
async def get_table_schema(table_name: str):
    """Get table schema information."""
    try:
        schema = bronze_data.get_table_schema(table_name)
        return {"table": table_name, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 