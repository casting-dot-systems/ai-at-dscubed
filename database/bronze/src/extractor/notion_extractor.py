import os
from typing import List, Dict, Any, Optional

import pandas as pd
from notion_client import Client
from dotenv import load_dotenv

class NotionExtractor:
    """
    Notion data extractor that:
    - Fetches data from a Notion database
    - Transforms the data into a pandas DataFrame
    - Returns the processed data
    """
    
    def __init__(self, api_key: str, database_id: str):
        """
        Initialize NotionExtractor with API key and database ID.
        
        Args:
            api_key (str): Notion API key
            database_id (str): Notion database ID
        """
        if not api_key:
            raise ValueError("A Notion API Key must be provided in .env file")
        
        if not database_id:
            raise ValueError("A Notion Database ID must be provided in .env file")
            
        self.token = api_key
        self.database_id = database_id
        # Initialize Notion client
        self.client = Client(auth=self.token)
        self.logger = None
    
    def fetch_user_data(self) -> List[Dict[str, Any]]:
        """
        Fetch raw pages from the Notion Committee database with pagination.
        """
        results: List[Dict[str, Any]] = []
        has_more = True
        start_cursor: Optional[str] = None

        while has_more:
            response = self.client.databases.query(
                database_id=self.database_id,
                page_size=77,
                start_cursor=start_cursor
            )

            for page in response.get("results", []):
                props = page.get("properties", {})
                record = {
                    "name": self._get_property_value(props.get("Name"), "title"),
                    "role": self._get_property_value(props.get("Role"), "multi_select"),
                    "status": self._get_property_value(props.get("Status"), "rich_text"),
                    "team": self._get_property_value(props.get("Team"), "relation"),
                    "joined": self._get_property_value(props.get("Joined"), "select"),
                    "bio": self._get_property_value(props.get("Bio"), "rich_text"),
                    "email": self._get_property_value(props.get("Email (dscubed)"), "email"),
                    "discord_tag": self._get_property_value(props.get("Discord Tag"), "rich_text"),
                    "facebook": self._get_property_value(props.get("Facebook"), "url"),
                    "instagram": self._get_property_value(props.get("Instagram"), "url"),
                    "linkedin": self._get_property_value(props.get("LinkedIn"), "url"),
                    "working_on": self._get_property_value(props.get("I'm Working On"), "rich_text"),
                    "workload": self._get_property_value(props.get("My Workload Is"), "select"),
                    "last_edited_at": page.get("last_edited_time")
                }
                results.append(record)

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        return results
    
    def _get_property_value(self, prop: Dict[str, Any], prop_type: str) -> Any:
        """
        Extract the plain value from a Notion property.
        """
        if not prop:
            return ""

        try:
            if prop_type == "title":
                return prop.get("title", [{}])[0].get("plain_text", "")

            if prop_type == "rich_text":
                return prop.get("rich_text", [{}])[0].get("plain_text", "")

            if prop_type == "select":
                return prop.get("select", {}).get("name", "")

            if prop_type == "multi_select":
                return ", ".join(item.get("name", "") for item in prop.get("multi_select", []))

            if prop_type == "url":
                return prop.get("url", "")

            if prop_type == "date":
                return prop.get("date", {}).get("start", "")

            if prop_type == "email":
                return prop.get("email", "")

            if prop_type == "relation":
                names: List[str] = []
                for rel in prop.get("relation", []):
                    page_id = rel.get("id")
                    if not page_id:
                        continue
                    try:
                        page = self.client.pages.retrieve(page_id=page_id)
                        title_prop = page.get("properties", {}).get("Name", {})
                        if title_prop.get("title"):
                            names.append(title_prop["title"][0].get("plain_text", ""))
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Failed to retrieve related page {page_id}: {e}")
                return ", ".join(names)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting {prop_type}: {e}")

        return ""
    
    def transform_user_data(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert raw record list into a DataFrame with metadata.
        """
        df = pd.DataFrame(raw_data)
        keep = [
            "name", "role", "status", "team", "joined", "bio",
            "email", "discord_tag", "facebook", "instagram", "linkedin",
            "working_on", "workload", "last_edited_time"
        ]
        df = df[keep]
        return df
    
    def parse(self, input_path: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch and transform data into a single DataFrame.
        """
        raw = self.fetch_data()
        return self.transform_data(raw)
