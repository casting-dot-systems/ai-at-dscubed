#!/usr/bin/env python3
"""
Simple script to populate the internal_msg_members table.
This script transforms Discord channel member data to silver.internal_msg_members.
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
        with engine.connect() as conn:
            df.to_sql(
                table_name,
                conn,
                schema=schema,
                if_exists='replace',
                index=False
            )
        print(f"✓ Successfully wrote data to {schema}.{table_name}")
        
    except Exception as e:
        print(f"❌ Error writing to {table_name}: {str(e)}")
        raise

def get_committee_data(engine: Engine) -> pd.DataFrame:
    """Get committee data from silver.committee."""
    query = sa.text("SELECT member_id, discord_id FROM silver.committee")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def get_component_data(engine: Engine) -> pd.DataFrame:
    """Get component data from silver.internal_msg_component."""
    query = sa.text("SELECT component_id FROM silver.internal_msg_component")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def create_member_component_relationships(committee_df: pd.DataFrame, component_df: pd.DataFrame) -> pd.DataFrame:
    """Create member-component relationships.
    
    For now, we'll create relationships between all committee members and all components.
    In a real scenario, you might have specific Discord API calls to get actual channel membership.
    """
    
    if committee_df.empty or component_df.empty:
        return pd.DataFrame(columns=['member_id', 'component_id', 'role', 'joined_at', 'left_at', 'ingestion_timestamp'])
    
    # Create cartesian product of members and components
    members_components = []
    
    for _, member in committee_df.iterrows():
        for _, component in component_df.iterrows():
            members_components.append({
                'member_id': member['member_id'],
                'component_id': component['component_id'],
                'role': 'member',  # Default role
                'joined_at': None,  # Would need Discord API to get actual join time
                'left_at': None,    # Would need Discord API to get actual leave time
                'ingestion_timestamp': datetime.datetime.now()
            })
    
    return pd.DataFrame(members_components)

def main():
    """Main function to populate the internal_msg_members table."""
    print("Starting internal_msg_members population...")
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        # Execute DDL to create the silver table if it doesn't exist
        ddl_path = Path(__file__).parent.parent / "src" / "DDL" / "internal_msg_members.sql"
        execute_ddl(engine, str(ddl_path))
        
        # Get committee data
        committee_df = get_committee_data(engine)
        print(f"✓ Retrieved {len(committee_df)} committee members")
        
        if committee_df.empty:
            print("⚠️  No committee members found. Please populate silver.committee first.")
            return
        
        # Get component data
        component_df = get_component_data(engine)
        print(f"✓ Retrieved {len(component_df)} components")
        
        if component_df.empty:
            print("⚠️  No components found. Please run the component pipeline first.")
            return
        
        # Create member-component relationships
        members_df = create_member_component_relationships(committee_df, component_df)
        print(f"✓ Generated {len(members_df)} member-component relationships")
        
        if members_df.empty:
            print("⚠️  No member-component relationships generated.")
            return
        
        # Write to silver table
        write_dataframe(engine, members_df, 'internal_msg_members', 'silver')
        
        print("\n🎉 internal_msg_members population completed successfully!")
        print(f"Populated {len(members_df)} member-component relationships")
        print(f"   - {len(committee_df)} unique members")
        print(f"   - {len(component_df)} unique components")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 