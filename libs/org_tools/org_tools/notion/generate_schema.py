import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_notion_database_schemas():
    database_ids = [
        "918affd4ce0d4b8eb7604d972fd24826",
        "ed8ba37a719a47d7a796c2d373c794b9",
        "139594e5-2bd9-47af-93ca-bb72a35742d2",
        "55909df8-1f56-40c4-9327-bab99b4f97f5",
    ]

    # Get Notion API token from environment
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise ValueError("NOTION_TOKEN not found in environment variables")

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    schemas = {}

    for db_id in database_ids:
        # Fetch database schema
        url = f"https://api.notion.com/v1/databases/{db_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        database_data = response.json()
        schemas[db_id] = database_data

    # Save schemas to JSON file
    schema_file_path = os.path.join(os.path.dirname(__file__), "schema.json")
    with open(schema_file_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2, ensure_ascii=False)

    print(f"Schemas saved to: {schema_file_path}")
    return schemas


if __name__ == "__main__":
    get_notion_database_schemas()
