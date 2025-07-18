from typing import Optional, List, Dict, Any
from notion_client import Client

from .types import (
    EventProjectID, TaskID, TeamID, DocumentID,
    EventProject, Task, Team, Document,
    EventProjectType, EventProjectProgress, EventProjectPriority,
    TaskStatus, TaskPriority, DocumentStatus,
    NotionDate, RichText, Person,
    EventProjectProperties, TaskProperties, TeamProperties, DocumentProperties,
    EVENTS_PROJECTS_DB_ID, TASKS_DB_ID, TEAMS_DB_ID, DOCUMENTS_DB_ID
)
from .client import (
    get_notion_client,
    format_date_for_notion, format_rich_text_for_notion, format_people_for_notion, format_relation_for_notion,
    parse_date_from_notion, parse_rich_text_from_notion, parse_people_from_notion, parse_relation_from_notion,
    get_select_enum_value, get_notion_id_from_enum
)

class NotionCRUDError(Exception):
    """Base exception for Notion CRUD operations"""
    pass

# Events/Projects CRUD Operations

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
    tasks: Optional[List[TaskID]] = None
) -> EventProjectID:
    """Create a new event/project"""
    try:
        client = get_notion_client()
        
        properties = {
            EventProjectProperties.NAME: {
                "title": [{"text": {"content": name}}]
            }
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
            parent={"database_id": EVENTS_PROJECTS_DB_ID},
            properties=properties
        )
        
        return EventProjectID(response["id"])
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to create event/project: {str(e)}")

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
            name=props.get(EventProjectProperties.NAME, {}).get("title", [{}])[0].get("text", {}).get("content", ""),
            type=get_select_enum_value(EventProjectType, props.get(EventProjectProperties.TYPE, {}).get("select", {}).get("id", "")),
            progress=get_select_enum_value(EventProjectProgress, props.get(EventProjectProperties.PROGRESS, {}).get("select", {}).get("id", "")),
            priority=get_select_enum_value(EventProjectPriority, props.get(EventProjectProperties.PRIORITY, {}).get("select", {}).get("id", "")),
            description=parse_rich_text_from_notion(props.get(EventProjectProperties.DESCRIPTION, {}).get("rich_text", [])),
            text=parse_rich_text_from_notion(props.get(EventProjectProperties.TEXT, {}).get("rich_text", [])),
            location=parse_rich_text_from_notion(props.get(EventProjectProperties.LOCATION, {}).get("rich_text", [])),
            due_dates=parse_date_from_notion(props.get(EventProjectProperties.DUE_DATES, {}).get("date")),
            owner=parse_people_from_notion(props.get(EventProjectProperties.OWNER, {}).get("people", [])),
            allocated=parse_people_from_notion(props.get(EventProjectProperties.ALLOCATED, {}).get("people", [])),
            parent_item=[EventProjectID(id_) for id_ in parse_relation_from_notion(props.get(EventProjectProperties.PARENT_ITEM, {}).get("relation", []))],
            sub_item=[EventProjectID(id_) for id_ in parse_relation_from_notion(props.get(EventProjectProperties.SUB_ITEM, {}).get("relation", []))],
            team=[TeamID(id_) for id_ in parse_relation_from_notion(props.get(EventProjectProperties.TEAM, {}).get("relation", []))],
            documents=[DocumentID(id_) for id_ in parse_relation_from_notion(props.get(EventProjectProperties.DOCUMENTS, {}).get("relation", []))],
            tasks=[TaskID(id_) for id_ in parse_relation_from_notion(props.get(EventProjectProperties.TASKS, {}).get("relation", []))]
        )
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to get event/project: {str(e)}")

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
    tasks: Optional[List[TaskID]] = None
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
                "select": {"id": get_notion_id_from_enum(progress)} if progress else None
            }
        
        if priority is not None:
            properties[EventProjectProperties.PRIORITY] = {
                "select": {"id": get_notion_id_from_enum(priority)} if priority else None
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
        
        client.pages.update(
            page_id=event_project_id,
            properties=properties
        )
        
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to update event/project: {str(e)}")

def delete_event_project(event_project_id: EventProjectID) -> bool:
    """Delete an event/project (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(
            page_id=event_project_id,
            archived=True
        )
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to delete event/project: {str(e)}")

def query_event_projects(
    type: Optional[EventProjectType] = None,
    progress: Optional[EventProjectProgress] = None,
    priority: Optional[EventProjectPriority] = None,
    owner: Optional[List[Person]] = None,
    team: Optional[List[TeamID]] = None,
    limit: Optional[int] = None
) -> List[EventProject]:
    """Query event/projects with filters"""
    try:
        client = get_notion_client()
        
        filter_conditions = []
        
        if type:
            filter_conditions.append({
                "property": EventProjectProperties.TYPE,
                "select": {"equals": get_notion_id_from_enum(type)}
            })
        
        if progress:
            filter_conditions.append({
                "property": EventProjectProperties.PROGRESS,
                "select": {"equals": get_notion_id_from_enum(progress)}
            })
        
        if priority:
            filter_conditions.append({
                "property": EventProjectProperties.PRIORITY,
                "select": {"equals": get_notion_id_from_enum(priority)}
            })
        
        if owner:
            for person in owner:
                filter_conditions.append({
                    "property": EventProjectProperties.OWNER,
                    "people": {"contains": person.id}
                })
        
        if team:
            for team_id in team:
                filter_conditions.append({
                    "property": EventProjectProperties.TEAM,
                    "relation": {"contains": team_id}
                })
        
        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}
        
        query_params = {
            "database_id": EVENTS_PROJECTS_DB_ID
        }
        
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
        raise NotionCRUDError(f"Failed to query event/projects: {str(e)}")

# Task CRUD Operations

def create_task(
    name: str,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    description: Optional[List[RichText]] = None,
    task_progress: Optional[List[RichText]] = None,
    due_dates: Optional[NotionDate] = None,
    in_charge: Optional[List[Person]] = None,
    event_project: Optional[List[EventProjectID]] = None,
    team: Optional[List[TeamID]] = None,
    parent_task: Optional[List[TaskID]] = None,
    sub_task: Optional[List[TaskID]] = None,
    blocking: Optional[List[TaskID]] = None,
    blocked_by: Optional[List[TaskID]] = None
) -> TaskID:
    """Create a new task"""
    try:
        client = get_notion_client()
        
        properties = {
            TaskProperties.NAME: {
                "title": [{"text": {"content": name}}]
            }
        }
        
        if status:
            properties[TaskProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)}
            }
        
        if priority:
            properties[TaskProperties.PRIORITY] = {
                "select": {"id": get_notion_id_from_enum(priority)}
            }
        
        if description:
            properties[TaskProperties.DESCRIPTION] = {
                "rich_text": format_rich_text_for_notion(description)
            }
        
        if task_progress:
            properties[TaskProperties.TASK_PROGRESS] = {
                "rich_text": format_rich_text_for_notion(task_progress)
            }
        
        if due_dates:
            date_obj = format_date_for_notion(due_dates)
            if date_obj:
                properties[TaskProperties.DUE_DATES] = {"date": date_obj}
        
        if in_charge:
            properties[TaskProperties.IN_CHARGE] = {
                "people": format_people_for_notion(in_charge)
            }
        
        if event_project:
            properties[TaskProperties.EVENT_PROJECT] = {
                "relation": format_relation_for_notion(event_project)
            }
        
        if team:
            properties[TaskProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }
        
        if parent_task:
            properties[TaskProperties.PARENT_TASK] = {
                "relation": format_relation_for_notion(parent_task)
            }
        
        if sub_task:
            properties[TaskProperties.SUB_TASK] = {
                "relation": format_relation_for_notion(sub_task)
            }
        
        if blocking:
            properties[TaskProperties.BLOCKING] = {
                "relation": format_relation_for_notion(blocking)
            }
        
        if blocked_by:
            properties[TaskProperties.BLOCKED_BY] = {
                "relation": format_relation_for_notion(blocked_by)
            }
        
        response = client.pages.create(
            parent={"database_id": TASKS_DB_ID},
            properties=properties
        )
        
        return TaskID(response["id"])
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to create task: {str(e)}")

def get_task(task_id: TaskID) -> Optional[Task]:
    """Get a task by ID"""
    try:
        client = get_notion_client()
        response = client.pages.retrieve(page_id=task_id)
        
        if not response:
            return None
        
        props = response["properties"]
        
        return Task(
            id=TaskID(response["id"]),
            name=props.get(TaskProperties.NAME, {}).get("title", [{}])[0].get("text", {}).get("content", ""),
            status=get_select_enum_value(TaskStatus, props.get(TaskProperties.STATUS, {}).get("status", {}).get("id", "")),
            priority=get_select_enum_value(TaskPriority, props.get(TaskProperties.PRIORITY, {}).get("select", {}).get("id", "")),
            description=parse_rich_text_from_notion(props.get(TaskProperties.DESCRIPTION, {}).get("rich_text", [])),
            task_progress=parse_rich_text_from_notion(props.get(TaskProperties.TASK_PROGRESS, {}).get("rich_text", [])),
            due_dates=parse_date_from_notion(props.get(TaskProperties.DUE_DATES, {}).get("date")),
            in_charge=parse_people_from_notion(props.get(TaskProperties.IN_CHARGE, {}).get("people", [])),
            event_project=[EventProjectID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.EVENT_PROJECT, {}).get("relation", []))],
            team=[TeamID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.TEAM, {}).get("relation", []))],
            parent_task=[TaskID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.PARENT_TASK, {}).get("relation", []))],
            sub_task=[TaskID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.SUB_TASK, {}).get("relation", []))],
            blocking=[TaskID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.BLOCKING, {}).get("relation", []))],
            blocked_by=[TaskID(id_) for id_ in parse_relation_from_notion(props.get(TaskProperties.BLOCKED_BY, {}).get("relation", []))]
        )
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to get task: {str(e)}")

def update_task(
    task_id: TaskID,
    name: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    description: Optional[List[RichText]] = None,
    task_progress: Optional[List[RichText]] = None,
    due_dates: Optional[NotionDate] = None,
    in_charge: Optional[List[Person]] = None,
    event_project: Optional[List[EventProjectID]] = None,
    team: Optional[List[TeamID]] = None,
    parent_task: Optional[List[TaskID]] = None,
    sub_task: Optional[List[TaskID]] = None,
    blocking: Optional[List[TaskID]] = None,
    blocked_by: Optional[List[TaskID]] = None
) -> bool:
    """Update a task"""
    try:
        client = get_notion_client()
        
        properties = {}
        
        if name is not None:
            properties[TaskProperties.NAME] = {
                "title": [{"text": {"content": name}}]
            }
        
        if status is not None:
            properties[TaskProperties.STATUS] = {
                "status": {"id": get_notion_id_from_enum(status)} if status else None
            }
        
        if priority is not None:
            properties[TaskProperties.PRIORITY] = {
                "select": {"id": get_notion_id_from_enum(priority)} if priority else None
            }
        
        if description is not None:
            properties[TaskProperties.DESCRIPTION] = {
                "rich_text": format_rich_text_for_notion(description)
            }
        
        if task_progress is not None:
            properties[TaskProperties.TASK_PROGRESS] = {
                "rich_text": format_rich_text_for_notion(task_progress)
            }
        
        if due_dates is not None:
            date_obj = format_date_for_notion(due_dates)
            properties[TaskProperties.DUE_DATES] = {"date": date_obj}
        
        if in_charge is not None:
            properties[TaskProperties.IN_CHARGE] = {
                "people": format_people_for_notion(in_charge)
            }
        
        if event_project is not None:
            properties[TaskProperties.EVENT_PROJECT] = {
                "relation": format_relation_for_notion(event_project)
            }
        
        if team is not None:
            properties[TaskProperties.TEAM] = {
                "relation": format_relation_for_notion(team)
            }
        
        if parent_task is not None:
            properties[TaskProperties.PARENT_TASK] = {
                "relation": format_relation_for_notion(parent_task)
            }
        
        if sub_task is not None:
            properties[TaskProperties.SUB_TASK] = {
                "relation": format_relation_for_notion(sub_task)
            }
        
        if blocking is not None:
            properties[TaskProperties.BLOCKING] = {
                "relation": format_relation_for_notion(blocking)
            }
        
        if blocked_by is not None:
            properties[TaskProperties.BLOCKED_BY] = {
                "relation": format_relation_for_notion(blocked_by)
            }
        
        client.pages.update(
            page_id=task_id,
            properties=properties
        )
        
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to update task: {str(e)}")

def delete_task(task_id: TaskID) -> bool:
    """Delete a task (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(
            page_id=task_id,
            archived=True
        )
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to delete task: {str(e)}")

def query_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    in_charge: Optional[List[Person]] = None,
    event_project: Optional[List[EventProjectID]] = None,
    team: Optional[List[TeamID]] = None,
    limit: Optional[int] = None
) -> List[Task]:
    """Query tasks with filters"""
    try:
        client = get_notion_client()
        
        filter_conditions = []
        
        if status:
            filter_conditions.append({
                "property": TaskProperties.STATUS,
                "status": {"equals": get_notion_id_from_enum(status)}
            })
        
        if priority:
            filter_conditions.append({
                "property": TaskProperties.PRIORITY,
                "select": {"equals": get_notion_id_from_enum(priority)}
            })
        
        if in_charge:
            for person in in_charge:
                filter_conditions.append({
                    "property": TaskProperties.IN_CHARGE,
                    "people": {"contains": person.id}
                })
        
        if event_project:
            for project_id in event_project:
                filter_conditions.append({
                    "property": TaskProperties.EVENT_PROJECT,
                    "relation": {"contains": project_id}
                })
        
        if team:
            for team_id in team:
                filter_conditions.append({
                    "property": TaskProperties.TEAM,
                    "relation": {"contains": team_id}
                })
        
        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}
        
        query_params = {
            "database_id": TASKS_DB_ID
        }
        
        if filter_obj:
            query_params["filter"] = filter_obj
        
        if limit:
            query_params["page_size"] = limit
        
        response = client.databases.query(**query_params)
        
        results = []
        for page in response["results"]:
            task = get_task(TaskID(page["id"]))
            if task:
                results.append(task)
        
        return results
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to query tasks: {str(e)}")

# Team CRUD Operations

def create_team(
    name: str,
    person: Optional[List[Person]] = None,
    cover: Optional[List[str]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    committee: Optional[List[str]] = None,
    document: Optional[List[DocumentID]] = None
) -> TeamID:
    """Create a new team"""
    try:
        client = get_notion_client()
        
        properties = {
            TeamProperties.NAME: {
                "title": [{"text": {"content": name}}]
            }
        }
        
        if person:
            properties[TeamProperties.PERSON] = {
                "people": format_people_for_notion(person)
            }
        
        if cover:
            properties[TeamProperties.COVER] = {
                "files": [{"name": file_name} for file_name in cover]
            }
        
        if events_projects:
            properties[TeamProperties.EVENTS_PROJECTS] = {
                "relation": format_relation_for_notion(events_projects)
            }
        
        if committee:
            properties[TeamProperties.COMMITTEE] = {
                "relation": format_relation_for_notion(committee)
            }
        
        if document:
            properties[TeamProperties.DOCUMENT] = {
                "relation": format_relation_for_notion(document)
            }
        
        response = client.pages.create(
            parent={"database_id": TEAMS_DB_ID},
            properties=properties
        )
        
        return TeamID(response["id"])
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to create team: {str(e)}")

def get_team(team_id: TeamID) -> Optional[Team]:
    """Get a team by ID"""
    try:
        client = get_notion_client()
        response = client.pages.retrieve(page_id=team_id)
        
        if not response:
            return None
        
        props = response["properties"]
        
        return Team(
            id=TeamID(response["id"]),
            name=props.get(TeamProperties.NAME, {}).get("title", [{}])[0].get("text", {}).get("content", ""),
            person=parse_people_from_notion(props.get(TeamProperties.PERSON, {}).get("people", [])),
            cover=[file_obj.get("name", "") for file_obj in props.get(TeamProperties.COVER, {}).get("files", [])],
            events_projects=[EventProjectID(id_) for id_ in parse_relation_from_notion(props.get(TeamProperties.EVENTS_PROJECTS, {}).get("relation", []))],
            committee=parse_relation_from_notion(props.get(TeamProperties.COMMITTEE, {}).get("relation", [])),
            document=[DocumentID(id_) for id_ in parse_relation_from_notion(props.get(TeamProperties.DOCUMENT, {}).get("relation", []))]
        )
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to get team: {str(e)}")

def update_team(
    team_id: TeamID,
    name: Optional[str] = None,
    person: Optional[List[Person]] = None,
    cover: Optional[List[str]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    committee: Optional[List[str]] = None,
    document: Optional[List[DocumentID]] = None
) -> bool:
    """Update a team"""
    try:
        client = get_notion_client()
        
        properties = {}
        
        if name is not None:
            properties[TeamProperties.NAME] = {
                "title": [{"text": {"content": name}}]
            }
        
        if person is not None:
            properties[TeamProperties.PERSON] = {
                "people": format_people_for_notion(person)
            }
        
        if cover is not None:
            properties[TeamProperties.COVER] = {
                "files": [{"name": file_name} for file_name in cover]
            }
        
        if events_projects is not None:
            properties[TeamProperties.EVENTS_PROJECTS] = {
                "relation": format_relation_for_notion(events_projects)
            }
        
        if committee is not None:
            properties[TeamProperties.COMMITTEE] = {
                "relation": format_relation_for_notion(committee)
            }
        
        if document is not None:
            properties[TeamProperties.DOCUMENT] = {
                "relation": format_relation_for_notion(document)
            }
        
        client.pages.update(
            page_id=team_id,
            properties=properties
        )
        
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to update team: {str(e)}")

def delete_team(team_id: TeamID) -> bool:
    """Delete a team (archive it)"""
    try:
        client = get_notion_client()
        client.pages.update(
            page_id=team_id,
            archived=True
        )
        return True
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to delete team: {str(e)}")

def query_teams(
    person: Optional[List[Person]] = None,
    events_projects: Optional[List[EventProjectID]] = None,
    limit: Optional[int] = None
) -> List[Team]:
    """Query teams with filters"""
    try:
        client = get_notion_client()
        
        filter_conditions = []
        
        if person:
            for p in person:
                filter_conditions.append({
                    "property": TeamProperties.PERSON,
                    "people": {"contains": p.id}
                })
        
        if events_projects:
            for project_id in events_projects:
                filter_conditions.append({
                    "property": TeamProperties.EVENTS_PROJECTS,
                    "relation": {"contains": project_id}
                })
        
        filter_obj = None
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_obj = filter_conditions[0]
            else:
                filter_obj = {"and": filter_conditions}
        
        query_params = {
            "database_id": TEAMS_DB_ID
        }
        
        if filter_obj:
            query_params["filter"] = filter_obj
        
        if limit:
            query_params["page_size"] = limit
        
        response = client.databases.query(**query_params)
        
        results = []
        for page in response["results"]:
            team = get_team(TeamID(page["id"]))
            if team:
                results.append(team)
        
        return results
    
    except Exception as e:
        raise NotionCRUDError(f"Failed to query teams: {str(e)}")

# Document CRUD Operations

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
        raise NotionCRUDError(f"Failed to create document: {str(e)}")

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
        raise NotionCRUDError(f"Failed to get document: {str(e)}")

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
        raise NotionCRUDError(f"Failed to update document: {str(e)}")

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
        raise NotionCRUDError(f"Failed to delete document: {str(e)}")

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
        raise NotionCRUDError(f"Failed to query documents: {str(e)}")