import argparse
import os
import asyncio
from dotenv import load_dotenv
from brain.bronze.src.extractor.discord_extractor import DiscordExtractor
from brain.bronze.src.utils.pipeline import Pipeline, get_ddl_path
import sqlalchemy as sa

# TODO: integrate run_pipeline function from pipeline.py
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Discord data pipeline')
    parser.add_argument('--input-path', required=True, help='Path to input file')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    BOT_KEY = os.getenv('BOT_KEY')
    TEST_SERVER_ID = os.getenv('TEST_SERVER_ID')

    if not BOT_KEY or not TEST_SERVER_ID:
        raise ValueError("BOT_KEY and TEST_SERVER_ID must be set in .env file")
    
    # DISCORD CHANNELS --------------------------------------------------------------------- */
    discord_channels_extractor = DiscordExtractor()
    discord_channels_pipeline = Pipeline(schema='bronze')

    # Follows an ETL process
    raw_data = asyncio.run(discord_channels_extractor.fetch_discord_channels()) # Extract
    
    # Execute DDL to create table
    ddl_path = get_ddl_path('discord_channel.sql')
    discord_channels_pipeline.execute_ddl(ddl_path)
    
    # Transform and Load
    df = asyncio.run(discord_channels_extractor.parse_discord_data(raw_data))
    discord_channels_pipeline.write_dataframe(
        df=df,
        table_name='discord_channels',
        if_exists='append'
    )
    
    print("Discord channel pipeline completed successfully!")


if __name__ == "__main__":
    main() 


