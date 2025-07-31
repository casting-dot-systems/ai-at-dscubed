#!/usr/bin/env python3
"""
Simple script to populate the internal text channel meta table.
This script directly transforms bronze data to silver without using the pipeline classes.
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

def get_bronze_data(engine: Engine) -> pd.DataFrame:
    """Get Discord channel data from bronze.discord_relevant_channels where ingest = TRUE."""
    query = "SELECT * FROM bronze.discord_relevant_channels WHERE ingest = TRUE" # only ingests relevant channels
    return pd.read_sql(query, engine)

def transform_bronze_to_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze data to silver format."""
    df = bronze_df.copy()
    
    # Add silver-specific columns
    df['source_name'] = "Discord"
    df['channel_type'] = 'discord_channel'
    df['description'] = "___"
    # Use parent_id from bronze data - this will be category_id for channels in categories, NULL for root channels
    df['parent_id'] = df.get('parent_id', None)  # Use parent_id from bronze data
    # Use section_name from bronze data - this will be the category name for channels in categories, NULL for root channels
    df['section_name'] = df.get('section_name', None)  # Use section_name from bronze data
    df['date_created'] = df['channel_created_at']
    
    # Select only the columns needed for silver table
    return df[['channel_id', 
               'source_name', 
               'channel_type',
               'channel_name',
               'description',
               'parent_id',
               'section_name',
               'date_created']]

def main():
    """Main function to populate the internal text channel meta table."""
    print("Starting internal text channel meta population...")
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        # Execute DDL to create the silver table if it doesn't exist
        ddl_path = Path(__file__).parent.parent / "src" / "DDL" / "internal_text_channel_meta.sql"
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
        write_dataframe(engine, silver_df, 'internal_text_channel_meta', 'silver')
        
        print("\n🎉 Internal text channel meta population completed successfully!")
        print(f"Populated {len(silver_df)} channel records")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 