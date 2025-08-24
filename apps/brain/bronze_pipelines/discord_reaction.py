import argparse
import os
import asyncio
import json
from dotenv import load_dotenv
from data_source_extractors.discord_extractor import DiscordExtractor
from pipeline import Pipeline, get_ddl_path
import sqlalchemy as sa



def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Discord reaction data pipeline')
    parser.add_argument('--input-path', required=False, default='dummy', help='Path to input file (not used, kept for compatibility)')
    parser.add_argument('--output-format', choices=['json', 'csv'], default='json', help='Output format for validation')
    parser.add_argument('--validate-only', action='store_true', help='Only extract and output data, do not load to database')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    bot_key = os.getenv('BOT_KEY') 
    server_id = os.getenv('TEST_SERVER_ID')
    if not bot_key or not server_id:
        raise ValueError("Bot Key and Server ID must be set in .env file")

    # DISCORD REACTION --------------------------------------------------------------------- */
    discord_reaction_extractor = DiscordExtractor()

    raw_data = asyncio.run(discord_reaction_extractor.fetch_discord_reactions()) # Extract
    df = asyncio.run(discord_reaction_extractor.parse_discord_data(raw_data)) # Transform
    
    # Output for validation
    if args.output_format == 'json':
        print("=== EXTRACTED DISCORD REACTIONS DATA (JSON) ===")
        print(json.dumps(raw_data, indent=2))
    elif args.output_format == 'csv':
        print("=== EXTRACTED DISCORD REACTIONS DATA (CSV) ===")
        print(df.to_csv(index=False))
    
    print(f"\n=== SUMMARY ===")
    print(f"Total reactions extracted: {len(raw_data)}")
    
    # Only load to database if not in validate-only mode
    if not args.validate_only:
        discord_reaction_pipeline = Pipeline(schema='bronze')
        
        # Get the DDL file path - use relative path from current location
        ddl_path = '../../libs/brain/bronze/DDL/discord_reaction.sql'
        
        # Execute DDL to create table if needed
        discord_reaction_pipeline.execute_ddl(ddl_path)
        
        # Load data to database
        discord_reaction_pipeline.write_dataframe(
            df=df,
            table_name='discord_reaction',
            if_exists='append'
        )
        
        print("Pipeline completed successfully!")

if __name__ == "__main__":
    main() 

