import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from pathlib import Path
from typing import Optional
import sys
from data_source_extractors.notion_extractor import NotionExtractor
from pipeline import Pipeline

def main():
    load_dotenv()
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    NOTION_USERS_DATABASE_ID = os.getenv('NOTION_USERS_DATABASE_ID')
    notion_extractor = NotionExtractor(NOTION_API_KEY, NOTION_USERS_DATABASE_ID)
    notion_pipeline = Pipeline(
        ddl_filepath = 'ddl/create_bronze_table.sql',
        table_name = 'notion_users',
    )
    if notion_extractor.recreate_table:
        notion_pipeline.create_table()
    notion_pipeline.ingest_from_df(
        notion_extractor.transform_user_data(
            notion_extractor.fetch_user_data()
        )
    )
    notion_pipeline.test_run_status() 

if __name__ == "__main__":
    main()
