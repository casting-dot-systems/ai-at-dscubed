# Notion Database CRUD Generator Prompt

## Objective

Generate a comprehensive, fully-typed CRUD system for Notion databases using their schema definitions. This prompt creates type-safe operations with proper error handling, relationship management, and comprehensive demos.

## Prerequisites

You will need:
1. **Database Schema**: JSON schema file containing database structure (from Notion API)
2. **Environment**: Python environment with `notion-client` and `python-dotenv` packages
3. **Notion Token**: Set as `NOTION_TOKEN` environment variable

## Implementation Requirements

### 1. **Project Structure**

Create a modular structure with separate files for each database:

```
custom_tools/notion/raw/
├── __init__.py          # Clean exports from all modules
├── types.py             # All type definitions and enums
├── client.py            # Notion client utilities
├── database1.py         # Database 1 CRUD + demo
├── database2.py         # Database 2 CRUD + demo
└── database3.py         # Database 3 CRUD + demo
```

### 2. **Type System Implementation**

#### **Custom ID Types**
```python
from typing import NewType

# Create NewType for each database for type safety
DatabaseID = NewType("DatabaseID", str)
RelatedTableID = NewType("RelatedTableID", str)
PersonID = NewType("PersonID", str)
```

#### **Enum Mapping**
For each select/status property, create enums using **exact Notion property IDs**:

```python
from enum import Enum

class DatabaseStatus(Enum):
    # Use actual Notion property IDs from schema
    ACTIVE = "e07b4872-6baf-464e-8ad9-abf768286e49"
    INACTIVE = "80d361e4-d127-4e1b-b7bf-06e07e2b7890"
    # ... map all options
```

#### **Complex Types**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NotionDate:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    time_zone: Optional[str] = None

@dataclass
class RichText:
    content: str
    link: Optional[str] = None

@dataclass
class Person:
    id: PersonID
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
```

#### **Property ID Constants**
```python
class DatabaseProperties:
    # Use URL-encoded property IDs from schema
    NAME = "title"
    STATUS = "%3D%3DBK"
    CREATED_TIME = "created_time"
    # ... all properties
```

### 3. **Client Utilities**

#### **Singleton Client**
```python
class NotionClient:
    _instance: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            notion_token = os.getenv("NOTION_TOKEN")
            if not notion_token:
                raise ValueError("NOTION_TOKEN environment variable is not set")
            cls._instance = Client(auth=notion_token)
        return cls._instance
```

#### **Format Conversion Functions**
- `format_date_for_notion()` - Python datetime to Notion date
- `format_rich_text_for_notion()` - Python objects to Notion rich text
- `format_people_for_notion()` - Python Person objects to Notion people
- `format_relation_for_notion()` - Python IDs to Notion relations
- `parse_*_from_notion()` - Reverse conversion functions
- `get_select_enum_value()` - Map Notion IDs to enum values

### 4. **CRUD Operations Per Database**

For each database, implement these functions:

#### **Create Function**
```python
def create_database_record(
    name: str,
    status: Optional[DatabaseStatus] = None,
    # ... all other properties as optional parameters
) -> DatabaseID:
    """Create a new database record"""
    try:
        client = get_notion_client()
        
        properties = {
            DatabaseProperties.NAME: {
                "title": [{"text": {"content": name}}]
            }
        }
        
        # Add each property conditionally
        if status:
            properties[DatabaseProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)}
            }
        
        response = client.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )
        
        return DatabaseID(response["id"])
    
    except Exception as e:
        raise DatabaseCRUDError(f"Failed to create record: {str(e)}")
```

#### **Read Function**
```python
def get_database_record(record_id: DatabaseID) -> Optional[DatabaseRecord]:
    """Get a record by ID"""
    try:
        client = get_notion_client()
        response = client.pages.retrieve(page_id=record_id)
        
        if not response:
            return None
        
        props = response["properties"]
        
        return DatabaseRecord(
            id=DatabaseID(response["id"]),
            name=props.get(DatabaseProperties.NAME, {}).get("title", [{}])[0].get("text", {}).get("content", ""),
            status=get_select_enum_value(DatabaseStatus, props.get(DatabaseProperties.STATUS, {}).get("status", {}).get("id", "")),
            # ... parse all properties
        )
    
    except Exception as e:
        raise DatabaseCRUDError(f"Failed to get record: {str(e)}")
```

#### **Update Function**
```python
def update_database_record(
    record_id: DatabaseID,
    name: Optional[str] = None,
    status: Optional[DatabaseStatus] = None,
    # ... all properties as optional parameters
) -> bool:
    """Update a record"""
    try:
        client = get_notion_client()
        
        properties = {}
        
        # Only update provided fields
        if name is not None:
            properties[DatabaseProperties.NAME] = {
                "title": [{"text": {"content": name}}]
            }
        
        if status is not None:
            properties[DatabaseProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)} if status else None
            }
        
        client.pages.update(
            page_id=record_id,
            properties=properties
        )
        
        return True
    
    except Exception as e:
        raise DatabaseCRUDError(f"Failed to update record: {str(e)}")
```

#### **Delete Function**
```python
def delete_database_record(record_id: DatabaseID) -> bool:
    """Delete a record (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(
            page_id=record_id,
            archived=True
        )
        return True
    
    except Exception as e:
        raise DatabaseCRUDError(f"Failed to delete record: {str(e)}")
```

#### **Query Function**
```python
def query_database_records(
    status: Optional[DatabaseStatus] = None,
    # ... filter parameters
    limit: Optional[int] = None
) -> List[DatabaseRecord]:
    """Query records with filters"""
    try:
        client = get_notion_client()
        
        filter_conditions = []
        
        if status:
            filter_conditions.append({
                "property": DatabaseProperties.STATUS,
                "status": {"equals": get_notion_id_from_enum(status)}
            })
        
        # Build filter object
        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}
        
        query_params = {"database_id": DATABASE_ID}
        
        if filter_obj:
            query_params["filter"] = filter_obj
        
        if limit:
            query_params["page_size"] = limit
        
        response = client.databases.query(**query_params)
        
        results = []
        for page in response["results"]:
            record = get_database_record(DatabaseID(page["id"]))
            if record:
                results.append(record)
        
        return results
    
    except Exception as e:
        raise DatabaseCRUDError(f"Failed to query records: {str(e)}")
```

### 5. **Demo Implementation**

Each database module MUST include a comprehensive demo in the `__main__` block:

```python
if __name__ == "__main__":
    """Demo of Database CRUD operations"""
    print("=== Database CRUD Demo ===")
    
    try:
        # 1. Create a new record
        print("\n1. Creating a new record...")
        record_id = create_database_record(
            name="Demo Record",
            status=DatabaseStatus.ACTIVE
        )
        print(f"✅ Created record with ID: {record_id}")
        
        # 2. Get the record
        print("\n2. Retrieving the record...")
        record = get_database_record(record_id)
        if record:
            print(f"✅ Retrieved record: {record.name}")
            print(f"   Status: {record.status}")
        
        # 3. Update the record
        print("\n3. Updating record...")
        update_success = update_database_record(
            record_id,
            status=DatabaseStatus.INACTIVE
        )
        if update_success:
            print("✅ Updated record status")
        
        # 4. Query records
        print("\n4. Querying records...")
        records = query_database_records(
            status=DatabaseStatus.INACTIVE,
            limit=5
        )
        print(f"✅ Found {len(records)} inactive records")
        
        # 5. Test relationships (if applicable)
        print("\n5. Testing relationships...")
        # Create related records and test connections
        
        # 6. Clean up - delete demo records
        print("\n6. Cleaning up demo records...")
        delete_database_record(record_id)
        print("✅ Demo records archived")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
    
    print("\n=== Demo Complete ===")
```

### 6. **Error Handling**

Create custom exception classes per database:

```python
class DatabaseCRUDError(Exception):
    """Exception for Database CRUD operations"""
    pass
```

### 7. **Module Exports**

Update `__init__.py` to export all functions and types:

```python
from .database1 import (
    create_database1_record, get_database1_record, update_database1_record,
    delete_database1_record, query_database1_records, Database1CRUDError
)

__all__ = [
    # Types
    "Database1ID", "Database1", "Database1Status",
    # CRUD Functions
    "create_database1_record", "get_database1_record", "update_database1_record",
    "delete_database1_record", "query_database1_records",
    # Exceptions
    "Database1CRUDError"
]
```

## Schema Analysis Process

1. **Extract Database Information**:
   - Database ID from schema
   - Database title for naming
   - All property definitions

2. **Map Property Types**:
   - `title` → String with required validation
   - `select` → Enum with all option IDs
   - `status` → Enum with all status IDs
   - `people` → List of Person objects
   - `relation` → List of related IDs
   - `date` → NotionDate object
   - `rich_text` → List of RichText objects
   - `checkbox` → Boolean
   - `files` → List of file names/URLs

3. **Handle Relationships**:
   - Map `dual_property` relations bidirectionally
   - Handle `single_property` relations
   - Create appropriate type annotations

4. **Generate Property Constants**:
   - Use URL-encoded property IDs from schema
   - Create readable constant names

## Testing Strategy

1. **Unit Tests**: Test each CRUD operation individually
2. **Integration Tests**: Test cross-database relationships
3. **Demo Scripts**: Comprehensive demos for each database
4. **Error Handling**: Test exception cases and edge conditions

## Usage Instructions

1. **Preparation**:
   - Extract database schema using Notion API
   - Set up Python environment with required packages
   - Configure NOTION_TOKEN environment variable

2. **Generation**:
   - Use this prompt with the database schema
   - Generate all required files following the structure
   - Implement comprehensive demos for each database

3. **Testing**:
   - Run individual demo scripts: `python -m module.database1`
   - Verify all CRUD operations work correctly
   - Test relationship management

4. **Integration**:
   - Import functions from the raw module
   - Build higher-level abstractions on top
   - Integrate with existing systems

This approach provides a robust, type-safe foundation for Notion database operations that can be easily extended and maintained.