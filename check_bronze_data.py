#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

def check_bronze_data():
    engine = sa.create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        # Check discord_channel table
        try:
            result = conn.execute(sa.text('SELECT COUNT(*) FROM bronze.discord_channel'))
            count = result.fetchone()[0]
            print(f"Discord channels in bronze: {count}")
        except Exception as e:
            print(f"Error checking discord_channel: {e}")
        
        # Check discord_relevant_channels table
        try:
            result = conn.execute(sa.text('SELECT COUNT(*) FROM bronze.discord_relevant_channels'))
            count = result.fetchone()[0]
            print(f"Relevant channels in bronze: {count}")
        except Exception as e:
            print(f"Error checking discord_relevant_channels: {e}")

if __name__ == "__main__":
    check_bronze_data() 