#!/usr/bin/env python3
"""
Simple script to populate the internal_msg_component table.
This script directly transforms bronze data to silver without using the pipeline classes.
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

def get_bronze_data(engine: Engine) -> pd.DataFrame:
    """Get Discord channel data from bronze.discord_relevant_channels where ingest = TRUE."""
    query = sa.text("SELECT * FROM bronze.discord_relevant_channels WHERE ingest = TRUE") # only ingests relevant channels
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def transform_bronze_to_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze data to silver format."""
    df = bronze_df.copy()
    
    # Map bronze columns to new silver schema
    # bronze: channel_id, channel_name, channel_created_at, parent_id, section_name
    # silver: component_id, platform_name, component_type, parent_component_id, component_name, created_at, section_name
    
    silver_df = pd.DataFrame({
        'component_id': df['channel_id'],  # Map channel_id to component_id
        'platform_name': 'Discord',  # Set platform
        'component_type': 'discord_channel',  # Set component type
        'parent_component_id': df.get('parent_id', None),  # Map parent_id to parent_component_id
        'component_name': df['channel_name'],  # Map channel_name to component_name
        'created_at': df['channel_created_at'],  # Map channel_created_at to created_at
        'archived_at': None,  # Not available in bronze data
        'ingestion_timestamp': datetime.datetime.now(),  # Current timestamp
        'section_name': df.get('section_name', None)  # Map section_name
    })
    
    return silver_df

def main():
    """Main function to populate the internal_msg_component table."""
    print("Starting internal_msg_component population...")
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        # Execute DDL to create the silver table if it doesn't exist
        ddl_path = Path(__file__).parent.parent / "src" / "DDL" / "internal_msg_component.sql"
        execute_ddl(engine, str(ddl_path))
        
        # Get bronze data
        bronze_df = get_bronze_data(engine)
        print(f"✓ Retrieved {len(bronze_df)} records from bronze.discord_relevant_channels (where ingest=TRUE)")
        
        if bronze_df.empty:
            print("⚠️  No channels found with ingest=TRUE in bronze.discord_relevant_channels. Please run the bronze pipeline first or set ingest=TRUE for channels you want to process.")
            return
        
        # Transform the data
        silver_df = transform_bronze_to_silver(bronze_df)
        print(f"✓ Transformed data: {len(silver_df)} records")
        
        # Write to silver table
        write_dataframe(engine, silver_df, 'internal_msg_component', 'silver')
        
        print("\n🎉 internal_msg_component population completed successfully!")
        print(f"Populated {len(silver_df)} component records")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 