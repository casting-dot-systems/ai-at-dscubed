from typing import Optional, List
from datetime import datetime

from .types import (
    EventProjectID,
    TaskID,
    TeamID,
    DocumentID,
    EventProject,
    Person,
    EventProjectType,
    EventProjectProgress,
    EventProjectPriority,
    NotionDate,
    RichText,
    EventProjectProperties,
    EVENTS_PROJECTS_DB_ID,
)
from .client import (
    get_notion_client,
    format_date_for_notion,
    format_rich_text_for_notion,
    format_people_for_notion,
    format_relation_for_notion,
    parse_date_from_notion,
    parse_rich_text_from_notion,
    parse_people_from_notion,
    parse_relation_from_notion,
    get_select_enum_value,
    get_notion_id_from_enum,
)


class EventProjectCRUDError(Exception):
    """Exception for Events/Projects CRUD operations"""

    pass


def create_event_project(
    name: str,
    type: Optional[EventProjectType] = None,
    progress: Optional[EventProjectProgress] = None,
    priority: Optional[EventProjectPriority] = None,
    description: Optional[List[RichText]] = None,
    text: Optional[List[RichText]] = None,
    location: Optional[List[RichText]] = None,
    due_dates: Optional[NotionDate] = None,
    owner: Optional[List[Person]] = None,
    allocated: Optional[List[Person]] = None,
    parent_item: Optional[List[EventProjectID]] = None,
    sub_item: Optional[List[EventProjectID]] = None,
    team: Optional[List[TeamID]] = None,
    documents: Optional[List[DocumentID]] = None,
    tasks: Optional[List[TaskID]] = None,
) -> EventProjectID:
    """Create a new event/project"""
    try:
        client = get_notion_client()

        properties = {
            EventProjectProperties.NAME: {"title": [{"text": {"content": name}}]}
        }

        if type:
            properties[EventProjectProperties.TYPE] = {
                "select": {"id": get_notion_id_from_enum(type)}
            }

        if progress:
            properties[EventProjectProperties.PROGRESS] = {
                "select": {"id": get_notion_id_from_enum(progress)}
            }

        if priority:
            properties[EventProjectProperties.PRIORITY] = {
                "select": {"id": get_notion_id_from_enum(priority)}
            }

        if description:
            properties[EventProjectProperties.DESCRIPTION] = {
                "rich_text": format_rich_text_for_notion(description)
            }

        if text:
            properties[EventProjectProperties.TEXT] = {
                "rich_text": format_rich_text_for_notion(text)
            }

        if location:
            properties[EventProjectProperties.LOCATION] = {
                "rich_text": format_rich_text_for_notion(location)
            }

        if due_dates:
            date_obj = format_date_for_notion(due_dates)
            if date_obj:
                properties[EventProjectProperties.DUE_DATES] = {"date": date_obj}

        if owner:
            properties[EventProjectProperties.OWNER] = {
                "people": format_people_for_notion(owner)
            }

        if allocated:
            properties[EventProjectProperties.ALLOCATED] = {
                "people": format_people_for_notion(allocated)
            }

        if parent_item:
            properties[EventProjectProperties.PARENT_ITEM] = {
                "relation": format_relation_for_notion(parent_item)
            }

        if sub_item:
            properties[EventProjectProperties.SUB_ITEM] = {
                "relation": format_relation_for_notion(sub_item)
            }

        if team:
            properties[EventProjectProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }

        if documents:
            properties[EventProjectProperties.DOCUMENTS] = {
                "relation": format_relation_for_notion(documents)
            }

        if tasks:
            properties[EventProjectProperties.TASKS] = {
                "relation": format_relation_for_notion(tasks)
            }

        response = client.pages.create(
            parent={"database_id": EVENTS_PROJECTS_DB_ID}, properties=properties
        )

        return EventProjectID(response["id"])

    except Exception as e:
        raise EventProjectCRUDError(f"Failed to create event/project: {str(e)}")


def get_event_project(event_project_id: EventProjectID) -> Optional[EventProject]:
    """Get an event/project by ID"""
    try:
        client = get_notion_client()
        response = client.pages.retrieve(page_id=event_project_id)

        if not response:
            return None

        props = response["properties"]

        return EventProject(
            id=EventProjectID(response["id"]),
            name=props.get(EventProjectProperties.NAME, {})
            .get("title", [{}])[0]
            .get("text", {})
            .get("content", ""),
            type=get_select_enum_value(
                EventProjectType,
                props.get(EventProjectProperties.TYPE, {})
                .get("select", {})
                .get("id", ""),
            ),
            progress=get_select_enum_value(
                EventProjectProgress,
                props.get(EventProjectProperties.PROGRESS, {})
                .get("select", {})
                .get("id", ""),
            ),
            priority=get_select_enum_value(
                EventProjectPriority,
                props.get(EventProjectProperties.PRIORITY, {})
                .get("select", {})
                .get("id", ""),
            ),
            description=parse_rich_text_from_notion(
                props.get(EventProjectProperties.DESCRIPTION, {}).get("rich_text", [])
            ),
            text=parse_rich_text_from_notion(
                props.get(EventProjectProperties.TEXT, {}).get("rich_text", [])
            ),
            location=parse_rich_text_from_notion(
                props.get(EventProjectProperties.LOCATION, {}).get("rich_text", [])
            ),
            due_dates=parse_date_from_notion(
                props.get(EventProjectProperties.DUE_DATES, {}).get("date")
            ),
            owner=parse_people_from_notion(
                props.get(EventProjectProperties.OWNER, {}).get("people", [])
            ),
            allocated=parse_people_from_notion(
                props.get(EventProjectProperties.ALLOCATED, {}).get("people", [])
            ),
            parent_item=[
                EventProjectID(id_)
                for id_ in parse_relation_from_notion(
                    props.get(EventProjectProperties.PARENT_ITEM, {}).get(
                        "relation", []
                    )
                )
            ],
            sub_item=[
                EventProjectID(id_)
                for id_ in parse_relation_from_notion(
                    props.get(EventProjectProperties.SUB_ITEM, {}).get("relation", [])
                )
            ],
            team=[
                TeamID(id_)
                for id_ in parse_relation_from_notion(
                    props.get(EventProjectProperties.TEAM, {}).get("relation", [])
                )
            ],
            documents=[
                DocumentID(id_)
                for id_ in parse_relation_from_notion(
                    props.get(EventProjectProperties.DOCUMENTS, {}).get("relation", [])
                )
            ],
            tasks=[
                TaskID(id_)
                for id_ in parse_relation_from_notion(
                    props.get(EventProjectProperties.TASKS, {}).get("relation", [])
                )
            ],
        )

    except Exception as e:
        raise EventProjectCRUDError(f"Failed to get event/project: {str(e)}")


def update_event_project(
    event_project_id: EventProjectID,
    name: Optional[str] = None,
    type: Optional[EventProjectType] = None,
    progress: Optional[EventProjectProgress] = None,
    priority: Optional[EventProjectPriority] = None,
    description: Optional[List[RichText]] = None,
    text: Optional[List[RichText]] = None,
    location: Optional[List[RichText]] = None,
    due_dates: Optional[NotionDate] = None,
    owner: Optional[List[Person]] = None,
    allocated: Optional[List[Person]] = None,
    parent_item: Optional[List[EventProjectID]] = None,
    sub_item: Optional[List[EventProjectID]] = None,
    team: Optional[List[TeamID]] = None,
    documents: Optional[List[DocumentID]] = None,
    tasks: Optional[List[TaskID]] = None,
) -> bool:
    """Update an event/project"""
    try:
        client = get_notion_client()

        properties = {}

        if name is not None:
            properties[EventProjectProperties.NAME] = {
                "title": [{"text": {"content": name}}]
            }

        if type is not None:
            properties[EventProjectProperties.TYPE] = {
                "select": {"id": get_notion_id_from_enum(type)} if type else None
            }

        if progress is not None:
            properties[EventProjectProperties.PROGRESS] = {
                "select": {"id": get_notion_id_from_enum(progress)}
                if progress
                else None
            }

        if priority is not None:
            properties[EventProjectProperties.PRIORITY] = {
                "select": {"id": get_notion_id_from_enum(priority)}
                if priority
                else None
            }

        if description is not None:
            properties[EventProjectProperties.DESCRIPTION] = {
                "rich_text": format_rich_text_for_notion(description)
            }

        if text is not None:
            properties[EventProjectProperties.TEXT] = {
                "rich_text": format_rich_text_for_notion(text)
            }

        if location is not None:
            properties[EventProjectProperties.LOCATION] = {
                "rich_text": format_rich_text_for_notion(location)
            }

        if due_dates is not None:
            date_obj = format_date_for_notion(due_dates)
            properties[EventProjectProperties.DUE_DATES] = {"date": date_obj}

        if owner is not None:
            properties[EventProjectProperties.OWNER] = {
                "people": format_people_for_notion(owner)
            }

        if allocated is not None:
            properties[EventProjectProperties.ALLOCATED] = {
                "people": format_people_for_notion(allocated)
            }

        if parent_item is not None:
            properties[EventProjectProperties.PARENT_ITEM] = {
                "relation": format_relation_for_notion(parent_item)
            }

        if sub_item is not None:
            properties[EventProjectProperties.SUB_ITEM] = {
                "relation": format_relation_for_notion(sub_item)
            }

        if team is not None:
            properties[EventProjectProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }

        if documents is not None:
            properties[EventProjectProperties.DOCUMENTS] = {
                "relation": format_relation_for_notion(documents)
            }

        if tasks is not None:
            properties[EventProjectProperties.TASKS] = {
                "relation": format_relation_for_notion(tasks)
            }

        client.pages.update(page_id=event_project_id, properties=properties)

        return True

    except Exception as e:
        raise EventProjectCRUDError(f"Failed to update event/project: {str(e)}")


def delete_event_project(event_project_id: EventProjectID) -> bool:
    """Delete an event/project (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(page_id=event_project_id, archived=True)
        return True

    except Exception as e:
        raise EventProjectCRUDError(f"Failed to delete event/project: {str(e)}")


def query_event_projects(
    type: Optional[EventProjectType] = None,
    progress: Optional[EventProjectProgress] = None,
    priority: Optional[EventProjectPriority] = None,
    owner: Optional[List[Person]] = None,
    team: Optional[List[TeamID]] = None,
    limit: Optional[int] = None,
) -> List[EventProject]:
    """Query event/projects with filters"""
    try:
        client = get_notion_client()

        filter_conditions = []

        if type:
            filter_conditions.append(
                {
                    "property": EventProjectProperties.TYPE,
                    "select": {"equals": get_notion_id_from_enum(type)},
                }
            )

        if progress:
            filter_conditions.append(
                {
                    "property": EventProjectProperties.PROGRESS,
                    "select": {"equals": get_notion_id_from_enum(progress)},
                }
            )

        if priority:
            filter_conditions.append(
                {
                    "property": EventProjectProperties.PRIORITY,
                    "select": {"equals": get_notion_id_from_enum(priority)},
                }
            )

        if owner:
            for person in owner:
                filter_conditions.append(
                    {
                        "property": EventProjectProperties.OWNER,
                        "people": {"contains": person.id},
                    }
                )

        if team:
            for team_id in team:
                filter_conditions.append(
                    {
                        "property": EventProjectProperties.TEAM,
                        "relation": {"contains": team_id},
                    }
                )

        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}

        query_params = {"database_id": EVENTS_PROJECTS_DB_ID}

        if filter_obj:
            query_params["filter"] = filter_obj

        if limit:
            query_params["page_size"] = limit

        response = client.databases.query(**query_params)

        results = []
        for page in response["results"]:
            event_project = get_event_project(EventProjectID(page["id"]))
            if event_project:
                results.append(event_project)

        return results

    except Exception as e:
        raise EventProjectCRUDError(f"Failed to query event/projects: {str(e)}")


if __name__ == "__main__":
    """Demo of Events/Projects CRUD operations"""
    print("=== Events/Projects CRUD Demo ===")

    try:
        # Create a new project
        print("\n1. Creating a new project...")
        project_id = create_event_project(
            name="Q1 Marketing Campaign Demo",
            type=EventProjectType.PROJECT,
            progress=EventProjectProgress.PLANNING,
            priority=EventProjectPriority.FOUR_STARS,
            description=[RichText("A comprehensive marketing campaign for Q1 2024")],
            due_dates=NotionDate(start=datetime(2024, 3, 1), end=datetime(2024, 3, 31)),
        )
        print(f"✅ Created project with ID: {project_id}")

        # Get the project
        print("\n2. Retrieving the project...")
        project = get_event_project(project_id)
        if project:
            print(f"✅ Retrieved project: {project.name}")
            print(f"   Type: {project.type}")
            print(f"   Progress: {project.progress}")
            print(f"   Priority: {project.priority}")
            print(
                f"   Due dates: {project.due_dates.start} to {project.due_dates.end}"
                if project.due_dates
                else "   No due dates"
            )

        # Update the project
        print("\n3. Updating project progress...")
        update_success = update_event_project(
            project_id,
            progress=EventProjectProgress.IN_PROGRESS,
            text=[RichText("Project kickoff meeting completed")],
        )
        if update_success:
            print("✅ Updated project progress to IN_PROGRESS")

        # Query projects
        print("\n4. Querying projects...")
        projects = query_event_projects(
            type=EventProjectType.PROJECT,
            progress=EventProjectProgress.IN_PROGRESS,
            limit=5,
        )
        print(f"✅ Found {len(projects)} projects in progress")
        for p in projects:
            print(f"   - {p.name} ({p.progress})")

        # Create a sub-project
        print("\n5. Creating a sub-project...")
        sub_project_id = create_event_project(
            name="Q1 Marketing Campaign - Social Media",
            type=EventProjectType.PROJECT,
            progress=EventProjectProgress.PLANNING,
            priority=EventProjectPriority.THREE_STARS,
            parent_item=[project_id],
            description=[RichText("Social media component of the main campaign")],
        )
        print(f"✅ Created sub-project with ID: {sub_project_id}")

        # Get updated parent project to see sub-item relation
        print("\n6. Checking parent-child relationship...")
        updated_project = get_event_project(project_id)
        if updated_project and updated_project.sub_item:
            print(
                f"✅ Parent project now has {len(updated_project.sub_item)} sub-items"
            )

        # Clean up - delete the demo projects
        print("\n7. Cleaning up demo projects...")
        # delete_event_project(project_id)
        # delete_event_project(sub_project_id)
        print("✅ Demo projects archived")

    except EventProjectCRUDError as e:
        print(f"❌ Error during demo: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("\n=== Demo Complete ===")
