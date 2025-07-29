#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

def check_discord_chats():
    engine = sa.create_engine(os.getenv('DATABASE_URL'))
    
    with engine.connect() as conn:
        # Check discord_chats table
        try:
            result = conn.execute(sa.text('SELECT COUNT(*) FROM bronze.discord_chats'))
            count = result.fetchone()[0]
            print(f"Discord chats in bronze: {count}")
            
            if count > 0:
                # Get a sample
                result = conn.execute(sa.text('SELECT channel_id, message_id, discord_user_id, content FROM bronze.discord_chats LIMIT 3'))
                samples = result.fetchall()
                print("\nSample messages:")
                for sample in samples:
                    print(f"  Channel: {sample[0]}, Message: {sample[1]}, User: {sample[2]}, Content: {sample[3][:50]}...")
                    
        except Exception as e:
            print(f"Error checking discord_chats: {e}")

if __name__ == "__main__":
    check_discord_chats() 