import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

from .types import (
    NotionDate, RichText, Person, PersonID,
    EventProjectType, EventProjectProgress, EventProjectPriority,
    TaskStatus, TaskPriority, DocumentStatus
)

load_dotenv()

class NotionClient:
    _instance: Optional[Client] = None

    def __new__(cls):
        """Create or return the singleton instance of the Notion client"""
        if cls._instance is None:
            notion_token = os.getenv("NOTION_TOKEN")
            if not notion_token:
                raise ValueError("NOTION_TOKEN environment variable is not set")
            cls._instance = Client(auth=notion_token)
        return cls._instance

def get_notion_client() -> Client:
    """Get the singleton Notion client instance"""
    return NotionClient()

def format_date_for_notion(date: Optional[NotionDate]) -> Optional[Dict[str, Any]]:
    """Convert NotionDate to Notion API format"""
    if not date:
        return None
    
    result = {}
    if date.start:
        result["start"] = date.start.isoformat()
    if date.end:
        result["end"] = date.end.isoformat()
    if date.time_zone:
        result["time_zone"] = date.time_zone
    
    return result if result else None

def format_rich_text_for_notion(rich_text: Optional[List[RichText]]) -> List[Dict[str, Any]]:
    """Convert RichText list to Notion API format"""
    if not rich_text:
        return []
    
    result = []
    for text in rich_text:
        rich_text_obj = {
            "type": "text",
            "text": {
                "content": text.content
            }
        }
        if text.link:
            rich_text_obj["text"]["link"] = {"url": text.link}
        result.append(rich_text_obj)
    
    return result

def format_people_for_notion(people: Optional[List[Person]]) -> List[Dict[str, str]]:
    """Convert Person list to Notion API format"""
    if not people:
        return []
    
    return [{"id": person.id} for person in people]

def format_relation_for_notion(ids: Optional[List[str]]) -> List[Dict[str, str]]:
    """Convert ID list to Notion relation format"""
    if not ids:
        return []
    
    return [{"id": id_} for id_ in ids]

def parse_date_from_notion(date_data: Optional[Dict[str, Any]]) -> Optional[NotionDate]:
    """Parse Notion date format to NotionDate"""
    if not date_data:
        return None
    
    start = None
    end = None
    time_zone = date_data.get("time_zone")
    
    if date_data.get("start"):
        start = datetime.fromisoformat(date_data["start"].replace("Z", "+00:00"))
    if date_data.get("end"):
        end = datetime.fromisoformat(date_data["end"].replace("Z", "+00:00"))
    
    return NotionDate(start=start, end=end, time_zone=time_zone)

def parse_rich_text_from_notion(rich_text_data: List[Dict[str, Any]]) -> List[RichText]:
    """Parse Notion rich text format to RichText list"""
    if not rich_text_data:
        return []
    
    result = []
    for text_obj in rich_text_data:
        content = text_obj.get("plain_text", "")
        link = None
        if text_obj.get("text", {}).get("link"):
            link = text_obj["text"]["link"]["url"]
        result.append(RichText(content=content, link=link))
    
    return result

def parse_people_from_notion(people_data: List[Dict[str, Any]]) -> List[Person]:
    """Parse Notion people format to Person list"""
    if not people_data:
        return []
    
    result = []
    for person_data in people_data:
        person = Person(
            id=PersonID(person_data["id"]),
            name=person_data.get("name"),
            avatar_url=person_data.get("avatar_url"),
            email=person_data.get("person", {}).get("email")
        )
        result.append(person)
    
    return result

def parse_relation_from_notion(relation_data: List[Dict[str, Any]]) -> List[str]:
    """Parse Notion relation format to ID list"""
    if not relation_data:
        return []
    
    return [rel["id"] for rel in relation_data]

def get_select_enum_value(enum_class, notion_id: str):
    """Get enum value from Notion select ID"""
    for enum_value in enum_class:
        if enum_value.value == notion_id:
            return enum_value
    return None

def get_notion_id_from_enum(enum_value) -> str:
    """Get Notion ID from enum value"""
    return enum_value.value if enum_value else None