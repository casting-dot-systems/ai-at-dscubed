import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd


class BronzeDataAccess:
    """Utility class for read-only access to bronze table data."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the data access utility.
        
        Args:
            database_url: Database connection string. If not provided, 
                         will try to load from DATABASE_URL environment variable.
        """
        if database_url:
            self.database_url = database_url
        else:
            # Load from environment
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / ".env"
            load_dotenv(dotenv_path=env_path, override=True)
            self.database_url = os.getenv("DATABASE_URL")
            if not self.database_url:
                raise ValueError("DATABASE_URL must be set in environment or provided directly")
        
        self.engine = create_engine(self.database_url)
    
    def get_discord_channels(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get Discord channel data from bronze.discord_channel."""
        query = "SELECT * FROM bronze.discord_channel"
        if limit:
            query += f" LIMIT {limit}"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row) for row in result.mappings()]
    
    def get_discord_chats(self, 
                         channel_id: Optional[int] = None,
                         user_id: Optional[int] = None,
                         days_back: Optional[int] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get Discord chat data from bronze.discord_chats with optional filters.
        
        Args:
            channel_id: Filter by specific channel ID
            user_id: Filter by specific user ID
            days_back: Filter by messages from last N days
            limit: Limit number of results
        """
        query = "SELECT * FROM bronze.discord_chats WHERE 1=1"
        params = {}
        
        if channel_id:
            query += " AND channel_id = :channel_id"
            params['channel_id'] = channel_id
        
        if user_id:
            query += " AND discord_user_id = :user_id"
            params['user_id'] = user_id
        
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            query += " AND chat_created_at >= :cutoff_date"
            params['cutoff_date'] = cutoff_date
        
        query += " ORDER BY chat_created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [dict(row) for row in result.mappings()]
    
    def get_committee_members(self) -> List[Dict[str, Any]]:
        """Get committee member data from bronze.committee."""
        query = "SELECT * FROM bronze.committee ORDER BY name"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row) for row in result.mappings()]
    
    def get_relevant_channels(self) -> List[Dict[str, Any]]:
        """Get relevant Discord channels from bronze.discord_relevant_channels."""
        query = "SELECT * FROM bronze.discord_relevant_channels ORDER BY channel_name"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row) for row in result.mappings()]
    
    def get_dataframe(self, table_name: str, schema: str = 'bronze') -> pd.DataFrame:
        """
        Get data as a pandas DataFrame.
        
        Args:
            table_name: Name of the table
            schema: Schema name (default: bronze)
        """
        query = f"SELECT * FROM {schema}.{table_name}"
        return pd.read_sql(query, self.engine)
    
    def get_table_schema(self, table_name: str, schema: str = 'bronze') -> List[Dict[str, Any]]:
        """Get table schema information."""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = :schema AND table_name = :table_name
        ORDER BY ordinal_position
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'schema': schema,
                'table_name': table_name
            })
            return [dict(row) for row in result.mappings()]


# Convenience function for quick access
def get_bronze_data(database_url: Optional[str] = None) -> BronzeDataAccess:
    """Get a BronzeDataAccess instance."""
    return BronzeDataAccess(database_url)


# Example usage
if __name__ == "__main__":
    # Example of how someone would use this
    bronze = BronzeDataAccess()
    
    # Get recent Discord chats
    recent_chats = bronze.get_discord_chats(days_back=7, limit=10)
    print(f"Found {len(recent_chats)} recent chats")
    
    # Get committee members
    members = bronze.get_committee_members()
    print(f"Found {len(members)} committee members")
    
    # Get table schema
    schema = bronze.get_table_schema('discord_chats')
    print("Discord chats table schema:")
    for col in schema:
        print(f"  {col['column_name']}: {col['data_type']}") 