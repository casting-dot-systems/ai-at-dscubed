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

def get_committee_data(engine: Engine) -> pd.DataFrame:
    """Get committee data from silver.committee for member_id lookup."""
    query = "SELECT member_id, discord_id FROM silver.committee"
    return pd.read_sql(query, engine)

def transform_bronze_to_silver_messages(bronze_df: pd.DataFrame, committee_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze chat data to silver messages format with proper member_id lookup.
    
    Committee members get their member_id from the committee table.
    Non-committee members get negative discord_user_id as member_id for identification.
    """
    df = bronze_df.copy()
    
    # Create a mapping from discord_id to member_id
    discord_to_member = dict(zip(committee_df['discord_id'], committee_df['member_id']))
    
    # Map bronze columns to silver columns
    # bronze: message_id, discord_user_id, channel_id, content, chat_created_at
    # silver: message_id, member_id, channel_id, message, date_created
    
    # Map discord_user_id to member_id using committee lookup
    df['member_id'] = df['discord_user_id'].map(discord_to_member)
    
    # Handle non-committee members: use negative discord_user_id to distinguish them
    unmapped_mask = df['member_id'].isna()
    unmapped_users = df[unmapped_mask]['discord_user_id'].unique()
    
    if len(unmapped_users) > 0:
        print(f"ℹ️  Found {len(unmapped_users)} Discord user IDs not in committee table (non-committee members):")
        for user_id in unmapped_users:
            print(f"   - {user_id}")
        print("   These will be labeled as non-committee members using negative member_id.")
    
    # For non-committee members, use negative discord_user_id as member_id
    df.loc[unmapped_mask, 'member_id'] = -df.loc[unmapped_mask, 'discord_user_id']
    
    silver_df = pd.DataFrame({
        'message_id': df['message_id'],
        'member_id': df['member_id'].astype(int),  # Positive: committee member_id, Negative: non-committee discord_user_id
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
        
        # Get committee data for member_id lookup
        committee_df = get_committee_data(engine)
        print(f"✓ Retrieved {len(committee_df)} records from silver.committee")
        
        if committee_df.empty:
            print("ℹ️  No data found in silver.committee. All Discord users will be treated as non-committee members.")
        
        # Transform the data
        silver_df = transform_bronze_to_silver_messages(bronze_df, committee_df)
        print(f"✓ Transformed data: {len(silver_df)} records")
        
        # Write to silver table
        write_dataframe(engine, silver_df, 'internal_text_channel_messages', 'silver')
        
        print("\n🎉 Internal text channel messages population completed successfully!")
        print(f"Populated {len(silver_df)} message records")
        
        # Show breakdown of committee vs non-committee messages
        committee_messages = len(silver_df[silver_df['member_id'] > 0])
        non_committee_messages = len(silver_df[silver_df['member_id'] < 0])
        print(f"   - Committee members: {committee_messages} messages")
        print(f"   - Non-committee members: {non_committee_messages} messages")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 