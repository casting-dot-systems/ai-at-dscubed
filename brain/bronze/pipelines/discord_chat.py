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
    bot_key = os.getenv('BOT_KEY') # Basically an authorised discord client
    server_id = os.getenv('TEST_SERVER_ID') # The server id of the AI server

    if not bot_key or not server_id:
        raise ValueError("Bot Key and Server ID must be set in .env file")

    # DISCORD CHAT --------------------------------------------------------------------- */
    discord_chat_extractor = DiscordExtractor(bot_key, server_id)
    discord_chat_pipeline = Pipeline(
        ddl_filepath = 'create_discord_chat_table.sql',
        table_name = 'discord_chat',
    )

    raw_data = asyncio.run(discord_chat_extractor.fetch_discord_chat()) # Extract
    if discord_chat_extractor.recreate_table:
        discord_chat_pipeline.create_table() # Transform                            
    discord_chat_pipeline.ingest_from_df(asyncio.run(discord_chat_extractor.parse_discord_data(raw_data))) # Load
    discord_chat_pipeline.test_run_status()

if __name__ == "__main__":
    main() 


