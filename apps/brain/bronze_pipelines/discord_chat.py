import argparse
import os
import asyncio
from dotenv import load_dotenv
<<<<<<< HEAD:brain/bronze/pipelines/discord_chat.py
from brain.bronze.src.extractor.discord_extractor import DiscordExtractor
from brain.bronze.src.utils.pipeline import Pipeline, get_ddl_path
=======
from data_source_extractors.discord_extractor import DiscordExtractor
from pipeline import Pipeline
import sqlalchemy as sa


>>>>>>> f/brain:apps/brain/bronze_pipelines/discord_chat.py

# TODO: integrate run_pipeline function from pipeline.py
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Discord chat data pipeline')
    parser.add_argument('--input-path', required=True, help='Path to input file')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    BOT_KEY = os.getenv('BOT_KEY')
    TEST_SERVER_ID = os.getenv('TEST_SERVER_ID')

    if not BOT_KEY or not TEST_SERVER_ID:
        raise ValueError("BOT_KEY and TEST_SERVER_ID must be set in .env file")

    # DISCORD CHAT PIPELINE
    discord_chat_extractor = DiscordExtractor()
    discord_chat_pipeline = Pipeline(schema='bronze')

    # Extract
    print("Fetching Discord chat data...")
    raw_data = asyncio.run(discord_chat_extractor.fetch_discord_chat())
    
    # Execute DDL to create table
    ddl_path = get_ddl_path('discord_chat.sql')
    discord_chat_pipeline.execute_ddl(ddl_path)
    
    # Transform and Load
    df = asyncio.run(discord_chat_extractor.parse_discord_data(raw_data))
    discord_chat_pipeline.write_dataframe(
        df=df,
        table_name='discord_chats',
        if_exists='append'
    )
    
    print("Discord chat pipeline completed successfully!")


if __name__ == "__main__":
    main() 


