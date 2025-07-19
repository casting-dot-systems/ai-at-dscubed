from typing import Optional, List

from .types import (
    DocumentID, EventProjectID, TeamID, Person,
    Document, DocumentStatus,
    DocumentProperties, DOCUMENTS_DB_ID
)
from .client import (
    get_notion_client,
    format_people_for_notion, format_relation_for_notion,
    parse_people_from_notion, parse_relation_from_notion,
    get_select_enum_value, get_notion_id_from_enum
)

class DocumentCRUDError(Exception):
    """Exception for Documents CRUD operations"""
    pass

def create_document(
    name: str,
    status: Optional[DocumentStatus] = None,
    person: Optional[List[Person]] = None,
    contributors: Optional[List[Person]] = None,
    owned_by: Optional[List[Person]] = None,
    in_charge: Optional[List[Person]] = None,
    team: Optional[List[TeamID]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    parent_item: Optional[List[DocumentID]] = None,
    sub_item: Optional[List[DocumentID]] = None,
    google_drive_file: Optional[List[str]] = None,
    pinned: Optional[bool] = None
) -> DocumentID:
    """Create a new document"""
    try:
        client = get_notion_client()
        
        properties = {
            DocumentProperties.NAME: {
                "title": [{"text": {"content": name}}]
            }
        }
        
        if status:
            properties[DocumentProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)}
            }
        
        if person:
            properties[DocumentProperties.PERSON] = {
                "people": format_people_for_notion(person)
            }
        
        if contributors:
            properties[DocumentProperties.CONTRIBUTORS] = {
                "people": format_people_for_notion(contributors)
            }
        
        if owned_by:
            properties[DocumentProperties.OWNED_BY] = {
                "people": format_people_for_notion(owned_by)
            }
        
        if in_charge:
            properties[DocumentProperties.IN_CHARGE] = {
                "people": format_people_for_notion(in_charge)
            }
        
        if team:
            properties[DocumentProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }
        
        if events_projects:
            properties[DocumentProperties.EVENTS_PROJECTS] = {
                "relation": format_relation_for_notion(events_projects)
            }
        
        if parent_item:
            properties[DocumentProperties.PARENT_ITEM] = {
                "relation": format_relation_for_notion(parent_item)
            }
        
        if sub_item:
            properties[DocumentProperties.SUB_ITEM] = {
                "relation": format_relation_for_notion(sub_item)
            }
        
        if google_drive_file:
            properties[DocumentProperties.GOOGLE_DRIVE_FILE] = {
                "relation": format_relation_for_notion(google_drive_file)
            }
        
        if pinned is not None:
            properties[DocumentProperties.PINNED] = {
                "checkbox": pinned
            }
        
        response = client.pages.create(
            parent={"database_id": DOCUMENTS_DB_ID},
            properties=properties
        )
        
        return DocumentID(response["id"])
    
    except Exception as e:
        raise DocumentCRUDError(f"Failed to create document: {str(e)}")

def get_document(document_id: DocumentID) -> Optional[Document]:
    """Get a document by ID"""
    try:
        client = get_notion_client()
        response = client.pages.retrieve(page_id=document_id)
        
        if not response:
            return None
        
        props = response["properties"]
        
        return Document(
            id=DocumentID(response["id"]),
            name=props.get(DocumentProperties.NAME, {}).get("title", [{}])[0].get("text", {}).get("content", ""),
            status=get_select_enum_value(DocumentStatus, props.get(DocumentProperties.STATUS, {}).get("status", {}).get("id", "")),
            person=parse_people_from_notion(props.get(DocumentProperties.PERSON, {}).get("people", [])),
            contributors=parse_people_from_notion(props.get(DocumentProperties.CONTRIBUTORS, {}).get("people", [])),
            owned_by=parse_people_from_notion(props.get(DocumentProperties.OWNED_BY, {}).get("people", [])),
            in_charge=parse_people_from_notion(props.get(DocumentProperties.IN_CHARGE, {}).get("people", [])),
            team=[TeamID(id_) for id_ in parse_relation_from_notion(props.get(DocumentProperties.TEAM, {}).get("relation", []))],
            events_projects=[EventProjectID(id_) for id_ in parse_relation_from_notion(props.get(DocumentProperties.EVENTS_PROJECTS, {}).get("relation", []))],
            parent_item=[DocumentID(id_) for id_ in parse_relation_from_notion(props.get(DocumentProperties.PARENT_ITEM, {}).get("relation", []))],
            sub_item=[DocumentID(id_) for id_ in parse_relation_from_notion(props.get(DocumentProperties.SUB_ITEM, {}).get("relation", []))],
            google_drive_file=parse_relation_from_notion(props.get(DocumentProperties.GOOGLE_DRIVE_FILE, {}).get("relation", [])),
            pinned=props.get(DocumentProperties.PINNED, {}).get("checkbox", False)
        )
    
    except Exception as e:
        raise DocumentCRUDError(f"Failed to get document: {str(e)}")

def update_document(
    document_id: DocumentID,
    name: Optional[str] = None,
    status: Optional[DocumentStatus] = None,
    person: Optional[List[Person]] = None,
    contributors: Optional[List[Person]] = None,
    owned_by: Optional[List[Person]] = None,
    in_charge: Optional[List[Person]] = None,
    team: Optional[List[TeamID]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    parent_item: Optional[List[DocumentID]] = None,
    sub_item: Optional[List[DocumentID]] = None,
    google_drive_file: Optional[List[str]] = None,
    pinned: Optional[bool] = None
) -> bool:
    """Update a document"""
    try:
        client = get_notion_client()
        
        properties = {}
        
        if name is not None:
            properties[DocumentProperties.NAME] = {
                "title": [{"text": {"content": name}}]
            }
        
        if status is not None:
            properties[DocumentProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)} if status else None
            }
        
        if person is not None:
            properties[DocumentProperties.PERSON] = {
                "people": format_people_for_notion(person)
            }
        
        if contributors is not None:
            properties[DocumentProperties.CONTRIBUTORS] = {
                "people": format_people_for_notion(contributors)
            }
        
        if owned_by is not None:
            properties[DocumentProperties.OWNED_BY] = {
                "people": format_people_for_notion(owned_by)
            }
        
        if in_charge is not None:
            properties[DocumentProperties.IN_CHARGE] = {
                "people": format_people_for_notion(in_charge)
            }
        
        if team is not None:
            properties[DocumentProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }
        
        if events_projects is not None:
            properties[DocumentProperties.EVENTS_PROJECTS] = {
                "relation": format_relation_for_notion(events_projects)
            }
        
        if parent_item is not None:
            properties[DocumentProperties.PARENT_ITEM] = {
                "relation": format_relation_for_notion(parent_item)
            }
        
        if sub_item is not None:
            properties[DocumentProperties.SUB_ITEM] = {
                "relation": format_relation_for_notion(sub_item)
            }
        
        if google_drive_file is not None:
            properties[DocumentProperties.GOOGLE_DRIVE_FILE] = {
                "relation": format_relation_for_notion(google_drive_file)
            }
        
        if pinned is not None:
            properties[DocumentProperties.PINNED] = {
                "checkbox": pinned
            }
        
        client.pages.update(
            page_id=document_id,
            properties=properties
        )
        
        return True
    
    except Exception as e:
        raise DocumentCRUDError(f"Failed to update document: {str(e)}")

def delete_document(document_id: DocumentID) -> bool:
    """Delete a document (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(
            page_id=document_id,
            archived=True
        )
        return True
    
    except Exception as e:
        raise DocumentCRUDError(f"Failed to delete document: {str(e)}")

def query_documents(
    status: Optional[DocumentStatus] = None,
    person: Optional[List[Person]] = None,
    team: Optional[List[TeamID]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    pinned: Optional[bool] = None,
    limit: Optional[int] = None
) -> List[Document]:
    """Query documents with filters"""
    try:
        client = get_notion_client()
        
        filter_conditions = []
        
        if status:
            filter_conditions.append({
                "property": DocumentProperties.STATUS,
                "status": {"equals": get_notion_id_from_enum(status)}
            })
        
        if person:
            for p in person:
                filter_conditions.append({
                    "property": DocumentProperties.PERSON,
                    "people": {"contains": p.id}
                })
        
        if team:
            for team_id in team:
                filter_conditions.append({
                    "property": DocumentProperties.TEAM,
                    "relation": {"contains": team_id}
                })
        
        if events_projects:
            for project_id in events_projects:
                filter_conditions.append({
                    "property": DocumentProperties.EVENTS_PROJECTS,
                    "relation": {"contains": project_id}
                })
        
        if pinned is not None:
            filter_conditions.append({
                "property": DocumentProperties.PINNED,
                "checkbox": {"equals": pinned}
            })
        
        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}
        
        query_params = {
            "database_id": DOCUMENTS_DB_ID
        }
        
        if filter_obj:
            query_params["filter"] = filter_obj
        
        if limit:
            query_params["page_size"] = limit
        
        response = client.databases.query(**query_params)
        
        results = []
        for page in response["results"]:
            document = get_document(DocumentID(page["id"]))
            if document:
                results.append(document)
        
        return results
    
    except Exception as e:
        raise DocumentCRUDError(f"Failed to query documents: {str(e)}")

if __name__ == "__main__":
    """Demo of Documents CRUD operations"""
    print("=== Documents CRUD Demo ===")
    
    try:
        # Create a new document
        print("\n1. Creating a new document...")
        document_id = create_document(
            name="Marketing Campaign Brief",
            status=DocumentStatus.NOT_STARTED,
            pinned=True
        )
        print(f"✅ Created document with ID: {document_id}")
        
        # Get the document
        print("\n2. Retrieving the document...")
        document = get_document(document_id)
        if document:
            print(f"✅ Retrieved document: {document.name}")
            print(f"   Status: {document.status}")
            print(f"   Pinned: {document.pinned}")
            print(f"   Contributors: {len(document.contributors) if document.contributors else 0}")
        
        # Update the document
        print("\n3. Updating document status...")
        update_success = update_document(
            document_id,
            status=DocumentStatus.IN_PROGRESS,
            pinned=False
        )
        if update_success:
            print("✅ Updated document status to IN_PROGRESS")
        
        # Create a parent document
        print("\n4. Creating a parent document...")
        parent_doc_id = create_document(
            name="Marketing Campaign Master Plan",
            status=DocumentStatus.IN_PROGRESS,
            pinned=True
        )
        print(f"✅ Created parent document with ID: {parent_doc_id}")
        
        # Update the first document to be a sub-document
        print("\n5. Creating parent-child relationship...")
        update_document(
            document_id,
            parent_item=[parent_doc_id]
        )
        print("✅ Set up parent-child relationship")
        
        # Create another sub-document
        print("\n6. Creating another sub-document...")
        sub_doc_id = create_document(
            name="Marketing Campaign Timeline",
            status=DocumentStatus.NOT_STARTED,
            parent_item=[parent_doc_id]
        )
        print(f"✅ Created sub-document with ID: {sub_doc_id}")
        
        # Query documents
        print("\n7. Querying documents...")
        documents = query_documents(
            status=DocumentStatus.IN_PROGRESS,
            limit=10
        )
        print(f"✅ Found {len(documents)} documents in progress")
        for d in documents:
            print(f"   - {d.name} (Pinned: {d.pinned})")
        
        # Query pinned documents
        print("\n8. Querying pinned documents...")
        pinned_docs = query_documents(
            pinned=True,
            limit=10
        )
        print(f"✅ Found {len(pinned_docs)} pinned documents")
        for d in pinned_docs:
            print(f"   - {d.name}")
        
        # Check parent-child relationships
        print("\n9. Checking document relationships...")
        updated_parent = get_document(parent_doc_id)
        if updated_parent and updated_parent.sub_item:
            print(f"✅ Parent document has {len(updated_parent.sub_item)} sub-documents")
        
        # Create a completed document
        print("\n10. Creating a completed document...")
        completed_doc_id = create_document(
            name="Marketing Campaign Results Report",
            status=DocumentStatus.DONE,
            pinned=False
        )
        print(f"✅ Created completed document with ID: {completed_doc_id}")
        
        # Query all documents to see the variety
        print("\n11. Final document overview...")
        all_docs = query_documents(limit=20)
        demo_docs = [d for d in all_docs if "Marketing Campaign" in d.name]
        print(f"✅ Found {len(demo_docs)} marketing campaign documents")
        
        statuses = {}
        for d in demo_docs:
            status = d.status.name if d.status else "None"
            statuses[status] = statuses.get(status, 0) + 1
        
        print("   Document status breakdown:")
        for status, count in statuses.items():
            print(f"     {status}: {count}")
        
        # Clean up - delete the demo documents
        print("\n12. Cleaning up demo documents...")
        delete_document(document_id)
        delete_document(parent_doc_id)
        delete_document(sub_doc_id)
        delete_document(completed_doc_id)
        print("✅ Demo documents archived")
        
    except DocumentCRUDError as e:
        print(f"❌ Error during demo: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n=== Demo Complete ===")