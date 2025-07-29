#!/usr/bin/env python3
"""
Simple script to populate the internal text channel messages table.
This script transforms bronze.discord_chats data to silver.internal_text_channel_messages.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.engine import Engine
import pandas as pd

# Load environment variables
load_dotenv()

def create_db_engine() -> Engine:
    """Create SQLAlchemy engine from environment variables."""
    db_connection = os.getenv("DATABASE_URL")
    if not db_connection:
        raise ValueError("DATABASE_URL must be set in .env file")
    return sa.create_engine(db_connection)

def execute_ddl(engine: Engine, ddl_path: str) -> None:
    """Execute DDL script."""
    try:
        with open(ddl_path, 'r') as f:
            ddl = f.read()
        
        with engine.connect() as conn:
            conn.execute(sa.text(ddl))
            conn.commit()
            
        print(f"✓ Successfully executed DDL: {ddl_path}")
        
    except Exception as e:
        print(f"❌ Error executing DDL {ddl_path}: {str(e)}")
        raise

def write_dataframe(engine: Engine, df: pd.DataFrame, table_name: str, schema: str = 'silver') -> None:
    """Write DataFrame to database."""
    try:
        df.to_sql(
            table_name,
            engine,
            schema=schema,
            if_exists='replace',
            index=False
        )
        print(f"✓ Successfully wrote data to {schema}.{table_name}")
        
    except Exception as e:
        print(f"❌ Error writing to {table_name}: {str(e)}")
        raise

def get_bronze_messages(engine: Engine) -> pd.DataFrame:
    """Get Discord chat data from bronze.discord_chats."""
    query = "SELECT * FROM bronze.discord_chats"
    return pd.read_sql(query, engine)

def transform_bronze_to_silver_messages(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze chat data to silver messages format."""
    df = bronze_df.copy()
    
    # Map bronze columns to silver columns
    # bronze: message_id, discord_user_id, channel_id, content, chat_created_at
    # silver: message_id, member_id, channel_id, message, date_created
    
    silver_df = pd.DataFrame({
        'message_id': df['message_id'],
        'member_id': df['discord_user_id'],  # Map discord_user_id to member_id
        'channel_id': df['channel_id'],
        'message': df['content'],  # Map content to message
        'date_created': df['chat_created_at']  # Map chat_created_at to date_created
    })
    
    return silver_df

def main():
    """Main function to populate the internal text channel messages table."""
    print("Starting internal text channel messages population...")
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        # Execute DDL to create the silver table if it doesn't exist
        ddl_path = Path(__file__).parent.parent / "src" / "DDL" / "internal_text_channel_messages.sql"
        execute_ddl(engine, str(ddl_path))
        
        # Get bronze data
        bronze_df = get_bronze_messages(engine)
        print(f"✓ Retrieved {len(bronze_df)} records from bronze.discord_chats")
        
        if bronze_df.empty:
            print("⚠️  No data found in bronze.discord_chats. Please run the bronze pipeline first.")
            return
        
        # Transform the data
        silver_df = transform_bronze_to_silver_messages(bronze_df)
        print(f"✓ Transformed data: {len(silver_df)} records")
        
        # Write to silver table
        write_dataframe(engine, silver_df, 'internal_text_channel_messages', 'silver')
        
        print("\n🎉 Internal text channel messages population completed successfully!")
        print(f"Populated {len(silver_df)} message records")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 