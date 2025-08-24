#!/usr/bin/env python3
"""
Simple script to populate the internal_msg_message table.
This script transforms bronze.discord_chats data to silver.internal_msg_message.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.engine import Engine
import pandas as pd
import datetime

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
    """Write DataFrame to database, preserving table schema including serial columns."""
    try:
        print(f"📊 About to write {len(df)} rows to {schema}.{table_name}")
        print(f"📊 DataFrame columns: {list(df.columns)}")
        print(f"📊 Sample data:")
        print(df.head(3))
        
        with engine.connect() as conn:
            # First, truncate the table to clear existing data but preserve schema
            conn.execute(sa.text(f"TRUNCATE TABLE {schema}.{table_name}"))
            
            # Then append data (preserves table schema including serial columns)
            df.to_sql(
                table_name,
                conn,
                schema=schema,
                if_exists='append',
                index=False
            )
            conn.commit()  # Explicit commit
        print(f"✓ Successfully wrote data to {schema}.{table_name}")
        
    except Exception as e:
        print(f"❌ Error writing to {table_name}: {str(e)}")
        raise

def get_bronze_messages(engine: Engine) -> pd.DataFrame:
    """Get Discord chat data from bronze.discord_chats."""
    query = sa.text("SELECT * FROM bronze.discord_chats")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def get_committee_data(engine: Engine) -> pd.DataFrame:
    """Get committee data from silver.committee for member_id lookup."""
    query = sa.text("SELECT member_id, discord_id FROM silver.committee")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def transform_bronze_to_silver_messages(bronze_df: pd.DataFrame, committee_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze chat data to silver messages format with proper member_id lookup.
    
    Committee members get their member_id from the committee table.
    Non-committee members get NULL as member_id (coerced to unknown).
    """
    df = bronze_df.copy()
    
    # Create a mapping from discord_id to member_id
    discord_to_member = dict(zip(committee_df['discord_id'], committee_df['member_id']))
    
    # Map bronze columns to silver columns
    # bronze: message_id, discord_user_id, channel_id, content, chat_created_at, chat_edited_at
    # silver: message_id (auto-generated), member_id, component_id, msg_txt, msg_type, sent_at, edited_at
    
    # Map discord_user_id to member_id using committee lookup
    df['member_id'] = df['discord_user_id'].map(discord_to_member)
    
    # Handle non-committee members: set to NULL (will be coerced to unknown)
    unmapped_mask = df['member_id'].isna()
    unmapped_users = df[unmapped_mask]['discord_user_id'].unique()
    
    if len(unmapped_users) > 0:
        print(f"ℹ️  Found {len(unmapped_users)} Discord user IDs not in committee table (non-committee members):")
        for user_id in unmapped_users:
            print(f"   - {user_id}")
        print("   These will be set to NULL (unknown member).")
    
    # For non-committee members, leave as NULL (no need to set negative values)
    
    # Determine message type based on thread information
    df['msg_type'] = df.apply(lambda row: 'thread_message' if row.get('is_thread', False) else 'channel_message', axis=1)
    
    silver_df = pd.DataFrame({
        'member_id': df['member_id'].astype('Int64'),  # Committee member_id or NULL for non-committee
        'component_id': df['channel_id'],  # Map channel_id to component_id
        'msg_txt': df['content'],  # Map content to msg_txt
        'msg_type': df['msg_type'],  # Message type (channel_message or thread_message)
        'sent_at': df['chat_created_at'],  # Map chat_created_at to sent_at
        'edited_at': df.get('chat_edited_at', None),  # Map chat_edited_at to edited_at
        'ingestion_timestamp': datetime.datetime.now()  # Current timestamp
    })
    
    return silver_df

def main():
    """Main function to populate the internal_msg_message table."""
    print("Starting internal_msg_message population...")
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        # Execute DDL to create the silver table if it doesn't exist
        ddl_path = Path(__file__).parent.parent / "src" / "DDL" / "internal_msg_message.sql"
        execute_ddl(engine, str(ddl_path))
        
        # Get bronze data
        bronze_df = get_bronze_messages(engine)
        print(f"✓ Retrieved {len(bronze_df)} records from bronze.discord_chats")
        
        if bronze_df.empty:
            print("⚠️  No data found in bronze.discord_chats. Please run the bronze pipeline first.")
            return
        
        # Get committee data for member_id lookup
        committee_df = get_committee_data(engine)
        print(f"✓ Retrieved {len(committee_df)} records from silver.committee")
        
        if committee_df.empty:
            print("ℹ️  No data found in silver.committee. All Discord users will be treated as non-committee members.")
        
        # Transform the data
        silver_df = transform_bronze_to_silver_messages(bronze_df, committee_df)
        print(f"✓ Transformed data: {len(silver_df)} records")
        
        # Write to silver table
        write_dataframe(engine, silver_df, 'internal_msg_message', 'silver')
        
        print("\n🎉 internal_msg_message population completed successfully!")
        print(f"Populated {len(silver_df)} message records")
        
        # Show breakdown of committee vs non-committee messages
        committee_messages = len(silver_df[silver_df['member_id'].notna()])
        non_committee_messages = len(silver_df[silver_df['member_id'].isna()])
        print(f"   - Committee members: {committee_messages} messages")
        print(f"   - Non-committee members: {non_committee_messages} messages")
        
        # Show breakdown by message type
        channel_messages = len(silver_df[silver_df['msg_type'] == 'channel_message'])
        thread_messages = len(silver_df[silver_df['msg_type'] == 'thread_message'])
        print(f"   - Channel messages: {channel_messages}")
        print(f"   - Thread messages: {thread_messages}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 