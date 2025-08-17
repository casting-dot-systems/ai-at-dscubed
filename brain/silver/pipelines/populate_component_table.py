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
    """Write DataFrame to database using SQL INSERT to avoid precision issues."""
    try:
        print("=== Writing data to database ===")
        
        with engine.connect() as conn:
            # Truncate table first to clear existing data but preserve schema
            conn.execute(sa.text(f"TRUNCATE TABLE {schema}.{table_name}"))
            
            # Temporarily disable foreign key constraint during insertion
            conn.execute(sa.text(f"ALTER TABLE {schema}.{table_name} DROP CONSTRAINT IF EXISTS internal_msg_component_parent_fk"))
            
            print("=== Inserting data using SQL INSERT statements ===")
            
            # Insert data row by row using SQL to preserve integer precision
            insert_sql = sa.text(f"""
                INSERT INTO {schema}.{table_name} (
                    component_id, platform_name, component_type, parent_component_id,
                    component_name, created_at, archived_at, ingestion_timestamp
                ) VALUES (
                    :component_id, :platform_name, :component_type, :parent_component_id,
                    :component_name, :created_at, :archived_at, :ingestion_timestamp
                )
            """)
            
            inserted_count = 0
            for _, row in df.iterrows():
                # Handle parent_component_id
                parent_id = None
                if pd.notna(row['parent_component_id']):
                    parent_id = int(row['parent_component_id'])
                
                conn.execute(insert_sql, {
                    'component_id': int(row['component_id']),
                    'platform_name': str(row['platform_name']),
                    'component_type': str(row['component_type']),
                    'parent_component_id': parent_id,
                    'component_name': str(row['component_name']),
                    'created_at': str(row['created_at']) if pd.notna(row['created_at']) else None,
                    'archived_at': str(row['archived_at']) if pd.notna(row['archived_at']) else None,
                    'ingestion_timestamp': row['ingestion_timestamp']
                })
                inserted_count += 1
            
            print(f"✓ Inserted {inserted_count} records using SQL")
            
            # Check for orphaned parent references
            print("=== Checking for orphaned parent references ===")
            result = conn.execute(sa.text(f"""
                SELECT DISTINCT p.parent_component_id, COUNT(*) as count
                FROM {schema}.{table_name} p
                LEFT JOIN {schema}.{table_name} c ON p.parent_component_id = c.component_id
                WHERE p.parent_component_id IS NOT NULL AND c.component_id IS NULL
                GROUP BY p.parent_component_id
            """))
            orphaned_count = 0
            for row in result:
                orphaned_count += row[1]
                print(f"Orphaned parent_id: {row[0]}, Children count: {row[1]}")
            
            if orphaned_count > 0:
                print(f"❌ Found {orphaned_count} records with orphaned parent references")
                print("⚠️  Skipping foreign key constraint due to orphaned references")
            else:
                # Re-enable the foreign key constraint
                conn.execute(sa.text(f"""
                    ALTER TABLE {schema}.{table_name} 
                    ADD CONSTRAINT internal_msg_component_parent_fk 
                    FOREIGN KEY (parent_component_id) REFERENCES {schema}.{table_name}(component_id)
                """))
                print("✅ Foreign key constraint added successfully")
            
            conn.commit()
            
        print(f"✓ Successfully wrote data to {schema}.{table_name}")
        
    except Exception as e:
        print(f"❌ Error writing to {table_name}: {str(e)}")
        raise

def get_bronze_data(engine: Engine) -> pd.DataFrame:
    """Get Discord channel data from bronze.discord_relevant_channels where ingest = TRUE."""
    # Explicitly cast ID columns to ensure they remain as integers and don't get converted to floats
    query = sa.text("""
        SELECT 
            server_id::BIGINT,
            server_name,
            channel_id::BIGINT,
            channel_name,
            channel_created_at,
            parent_id::BIGINT,
            entity_type,
            ingest,
            ingestion_timestamp
        FROM bronze.discord_relevant_channels 
        WHERE ingest = TRUE
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def transform_bronze_to_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Transform bronze data to silver format."""
    df = bronze_df.copy()
    
    # Debug: Print available columns and sample entity_type values
    print(f"📊 Bronze data columns: {list(df.columns)}")
    if 'entity_type' in df.columns:
        entity_type_counts = df['entity_type'].value_counts()
        print(f"📊 Entity type distribution: {entity_type_counts.to_dict()}")
        print("📊 Specific channel types detected:")
        for entity_type, count in entity_type_counts.items():
            if entity_type == 'discord_text_channel':
                print(f"   - Text channels: {count}")
            elif entity_type == 'discord_voice_channel':
                print(f"   - Voice channels: {count}")
            elif entity_type == 'discord_forum':
                print(f"   - Forum channels: {count}")
            elif entity_type == 'discord_section':
                print(f"   - Categories/Sections: {count}")
            elif entity_type == 'discord_news_channel':
                print(f"   - News channels: {count}")
            elif entity_type == 'discord_stage_channel':
                print(f"   - Stage voice channels: {count}")
            else:
                print(f"   - Other ({entity_type}): {count}")
    else:
        print("⚠️  Warning: entity_type column not found in bronze data")
    
    # Map bronze columns to new silver schema
    # bronze: channel_id, channel_name, channel_created_at, parent_id, entity_type
    # silver: component_id, platform_name, component_type, parent_component_id, component_name, created_at
    
    # Use entity_type from bronze data if available, otherwise default to discord_text_channel
    component_type = df.get('entity_type', 'discord_text_channel')
    if isinstance(component_type, pd.Series):
        # If entity_type is a series, use it as is
        component_type_values = component_type
    else:
        # If entity_type is a single value or None, fill with default
        component_type_values = 'discord_text_channel'
    
    silver_df = pd.DataFrame({
        'component_id': df['channel_id'],  # Map channel_id to component_id
        'platform_name': 'Discord',  # Set platform
        'component_type': component_type_values,  # Use actual entity_type from bronze
        'parent_component_id': df.get('parent_id', None),  # Map parent_id to parent_component_id
        'component_name': df['channel_name'],  # Map channel_name to component_name
        'created_at': df['channel_created_at'],  # Map channel_created_at to created_at
        'archived_at': None,  # Not available in bronze data
        'ingestion_timestamp': datetime.datetime.now(),  # Current timestamp
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