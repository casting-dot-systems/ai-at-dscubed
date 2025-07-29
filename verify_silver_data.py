#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import sqlalchemy as sa
import pandas as pd

load_dotenv()

def verify_silver_data():
    engine = sa.create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        # Check silver table
        try:
            result = conn.execute(sa.text('SELECT COUNT(*) FROM silver.internal_text_channel_meta'))
            count = result.fetchone()[0]
            print(f"Channels in silver.internal_text_channel_meta: {count}")
            
            # Get a sample of the data
            df = pd.read_sql("SELECT * FROM silver.internal_text_channel_meta LIMIT 5", engine)
            print("\nSample data:")
            print(df.to_string(index=False))
            
        except Exception as e:
            print(f"Error checking silver table: {e}")

if __name__ == "__main__":
    verify_silver_data() 