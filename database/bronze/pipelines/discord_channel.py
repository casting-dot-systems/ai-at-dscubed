import argparse
import os
import asyncio
from dotenv import load_dotenv
from bronze.extractors.discord_extractor import DiscordExtractor
from bronze.utils.pipeline import Pipeline
import sqlalchemy as sa



def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Discord data pipeline')
    parser.add_argument('--input-path', required=True, help='Path to input file')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    DARCY_KEY = os.getenv('DARCY_KEY') # Basically an authorised discord client
    TEST_SERVER_ID = os.getenv('TEST_SERVER_ID') # The server id of the AI server

    if not DARCY_KEY or not TEST_SERVER_ID:
        raise ValueError("DARCY_KEY and TEST_SERVER_ID must be set in .env file")
    
    # DISCORD CHANNELS --------------------------------------------------------------------- */
    discord_channels_extractor = DiscordExtractor(DARCY_KEY, TEST_SERVER_ID)
    discord_channels_pipeline = Pipeline(
        ddl_filepath = 'create_discord_channels_table.sql',
        table_name = 'discord_channels',
    )

    # Follows an ETL process
    raw_data = asyncio.run(discord_channels_extractor.fetch_discord_channels()) # Extract
    if discord_channels_extractor.recreate_table:
        discord_channels_pipeline.create_table() # Transform
    discord_channels_pipeline.ingest_from_df(asyncio.run(discord_channels_extractor.parse_discord_data(raw_data))) # Load
    discord_channels_pipeline.test_run_status()

if __name__ == "__main__":
    main() 


