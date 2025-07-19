from typing import Optional, List
from datetime import datetime

from .types import (
    TaskID, EventProjectID, TeamID, Person,
    Task, TaskStatus, TaskPriority,
    NotionDate, RichText,
    TaskProperties, TASKS_DB_ID
)
from .client import (
    get_notion_client,
    format_date_for_notion, format_rich_text_for_notion, format_people_for_notion, format_relation_for_notion,
    parse_date_from_notion, parse_rich_text_from_notion, parse_people_from_notion, parse_relation_from_notion,
    get_select_enum_value, get_notion_id_from_enum
)

class TaskCRUDError(Exception):
    """Exception for Tasks CRUD operations"""
    pass

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
        raise TaskCRUDError(f"Failed to create task: {str(e)}")

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
        raise TaskCRUDError(f"Failed to get task: {str(e)}")

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
        raise TaskCRUDError(f"Failed to update task: {str(e)}")

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
        raise TaskCRUDError(f"Failed to delete task: {str(e)}")

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
        raise TaskCRUDError(f"Failed to query tasks: {str(e)}")

if __name__ == "__main__":
    """Demo of Tasks CRUD operations"""
    print("=== Tasks CRUD Demo ===")
    
    try:
        # Create a new task
        print("\n1. Creating a new task...")
        task_id = create_task(
            name="Design marketing materials",
            status=TaskStatus.NOT_STARTED,
            priority=TaskPriority.HIGH,
            description=[RichText("Create visual designs for Q1 marketing campaign")],
            due_dates=NotionDate(
                start=datetime(2024, 2, 15),
                end=datetime(2024, 2, 28)
            )
        )
        print(f"✅ Created task with ID: {task_id}")
        
        # Get the task
        print("\n2. Retrieving the task...")
        task = get_task(task_id)
        if task:
            print(f"✅ Retrieved task: {task.name}")
            print(f"   Status: {task.status}")
            print(f"   Priority: {task.priority}")
            print(f"   Due dates: {task.due_dates.start} to {task.due_dates.end}" if task.due_dates else "   No due dates")
        
        # Update the task
        print("\n3. Updating task status...")
        update_success = update_task(
            task_id,
            status=TaskStatus.IN_PROGRESS,
            task_progress=[RichText("Started initial research and concept development")]
        )
        if update_success:
            print("✅ Updated task status to IN_PROGRESS")
        
        # Create a sub-task
        print("\n4. Creating a sub-task...")
        sub_task_id = create_task(
            name="Create logo variations",
            status=TaskStatus.NOT_STARTED,
            priority=TaskPriority.MEDIUM,
            description=[RichText("Design 3 different logo variations for the campaign")],
            parent_task=[task_id],
            due_dates=NotionDate(
                start=datetime(2024, 2, 16),
                end=datetime(2024, 2, 20)
            )
        )
        print(f"✅ Created sub-task with ID: {sub_task_id}")
        
        # Create a blocking task
        print("\n5. Creating a blocking task...")
        blocking_task_id = create_task(
            name="Approve brand guidelines",
            status=TaskStatus.NOT_STARTED,
            priority=TaskPriority.HIGH,
            description=[RichText("Get final approval on brand guidelines before design work")],
            blocking=[task_id],
            due_dates=NotionDate(
                start=datetime(2024, 2, 14),
                end=datetime(2024, 2, 15)
            )
        )
        print(f"✅ Created blocking task with ID: {blocking_task_id}")
        
        # Query tasks
        print("\n6. Querying tasks...")
        tasks = query_tasks(
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            limit=5
        )
        print(f"✅ Found {len(tasks)} high-priority tasks in progress")
        for t in tasks:
            print(f"   - {t.name} ({t.status})")
        
        # Query all tasks (no filters)
        print("\n7. Querying all recent tasks...")
        all_tasks = query_tasks(limit=10)
        print(f"✅ Found {len(all_tasks)} recent tasks")
        
        # Check parent-child relationships
        print("\n8. Checking task relationships...")
        updated_task = get_task(task_id)
        if updated_task:
            if updated_task.sub_task:
                print(f"✅ Parent task has {len(updated_task.sub_task)} sub-tasks")
            if updated_task.blocked_by:
                print(f"✅ Task is blocked by {len(updated_task.blocked_by)} other tasks")
        
        # Update task to completed
        print("\n9. Completing the sub-task...")
        update_task(sub_task_id, status=TaskStatus.DONE)
        print("✅ Sub-task marked as completed")
        
        # Clean up - delete the demo tasks
        print("\n10. Cleaning up demo tasks...")
        delete_task(task_id)
        delete_task(sub_task_id)
        delete_task(blocking_task_id)
        print("✅ Demo tasks archived")
        
    except TaskCRUDError as e:
        print(f"❌ Error during demo: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n=== Demo Complete ===")