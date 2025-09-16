import argparse
import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from data_source_extractors.discord_extractor import DiscordExtractor
from pipeline import Pipeline, get_ddl_path
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
    df = discord_channels_extractor.parse_discord_data(raw_data) # Transform (synchronous now)
    discord_channels_pipeline.write_dataframe(
        df=df,
        table_name='discord_channels',
        if_exists='replace' # Equivalent to truncate + insert in SQL
    )
    
    print("Discord channel pipeline completed successfully!")


if __name__ == "__main__":
    main() 


