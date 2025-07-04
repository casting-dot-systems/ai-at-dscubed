import os
from datetime import datetime
from enum import Enum
from typing import Any, Literal, NewType, Optional

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_LOOKUP = {
    "241085495398891521": {
        "name": "Nathan Luo",
        "role": "AI Director",
        "notion_id": "f746733c-66cc-4cbc-b553-c5d3f03ed240",
    },
    "373796704450772992": {
        "name": "Pranav Jayanty",
        "role": "AI Officer",
        "notion_id": "c005948c-9115-4a4d-b3c2-78286fa75fdb",
    },
    "1195065884713156728": {
        "name": "Antoine Dulauroy",
        "role": "AI Officer",
        "notion_id": "1bbd872b-594c-81f5-bc03-0002a7229ca6",
    },
}

NOTION_PRODUCTION_DATABASE_ID_TASKS: str = "ed8ba37a719a47d7a796c2d373c794b9"
NOTION_PRODUCTION_DATABASE_ID_PROJECTS: str = "918affd4ce0d4b8eb7604d972fd24826"


class TASK_STATUS(Enum):
    # AI: Using str as base class to maintain string values while having enum functionality
    NotStarted = "e07b4872-6baf-464e-8ad9-abf768286e49"
    InProgress = "80d361e4-d127-4e1b-b7bf-06e07e2b7890"
    Blocked = "rb_~"
    ToReview = "Q=S~"
    Done = "`acO"
    Archive = "aAlA"


class NotionClient:
    _instance: Optional[Client] = None

    def __new__(cls):
        """
        Create or return the singleton instance of the Notion client

        Returns:
            Client: The Notion client instance
        """
        if cls._instance is None:
            notion_token = os.getenv("NOTION_TOKEN")
            if not notion_token:
                raise ValueError("NOTION_TOKEN environment variable is not set")
            cls._instance = Client(auth=notion_token)
        return cls._instance


def get_all_users() -> list[dict[str, Any]]:
    """
    Get all users from the users database
    """
    notion_client : Client = NotionClient()
    response = notion_client.users.list()

    user_list: list[Any] = response.get("results", [])
    for user in user_list:
        print(user.get("id"), user.get("name"))
        user_list.append({
            "id": user.get("id"),
            "name": user.get("name"),
        })  # TODO use userdata?
    return user_list


def get_active_tasks(
    notion_user_id: Optional[str] = None,
    notion_project_id: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    """
    Get all active tasks from the tasks database with provided filters

    Args:
        notion_user_id: The NOTION user ID of the person in charge of the task (DO NOT USE DISCORD USER ID)
        notion_project_id: The ID of the project the task is associated with (need to call get_active_projects to get the list of projects and their ids)

    Returns:
        A list of tasks
    """
    notion_client : Client = NotionClient()
    # filter by Project AND UserID
    filter_obj = {
        "and": [
            {
                "property": "Status",
                "status": {"does_not_equal": "Done"},
            },
            {
                "property": "Status",
                "status": {"does_not_equal": "Archive"},
            },
        ]
    }
    if notion_project_id:
        filter_obj["and"].append({
            "property": "Event/Project",
            "relation": {"contains": notion_project_id},
        })
    if notion_user_id:
        filter_obj["and"].append({
            "property": "In Charge",
            "people": {"contains": notion_user_id},
        })

    # quering Task database
    response = notion_client.databases.query(
        database_id=NOTION_PRODUCTION_DATABASE_ID_TASKS,
        filter=filter_obj,  # should database id be notion_project_id?
    )

    tasks = response.get("results", [])
    parsed_tasks = {}
    for task in tasks:
        # Get properties safely
        properties = task.get("properties", {})

        # Parse name safely
        name = None
        name_prop = properties.get("Name", {})
        title_list = name_prop.get("title", [])
        if title_list and len(title_list) > 0:
            text_obj = title_list[0].get("text", {})
            name = text_obj.get("content")

        # Parse status safely
        status = None
        status_prop = properties.get("Status", {})
        status_obj = status_prop.get("status", {})
        if status_obj:
            status = status_obj.get("name")

        # Parse due date safely
        due_date = None
        due_date_prop = properties.get("Due Dates", {})
        date_obj = due_date_prop.get("date", {})
        if date_obj:
            due_date = date_obj.get("start")

        # Parse project safely
        project = None
        relation_prop = properties.get("Event/Project", {}) or properties.get("Event", {})
        relation_list = relation_prop.get("relation", [])
        if relation_list and len(relation_list) > 0:
            project = relation_list[0].get("id")

        # Parse userID in charge safely
        notion_user_id = None
        userID_inCharge_prop = properties.get("In Charge", {})
        userID_inCharge_list = userID_inCharge_prop.get("people", [])
        if userID_inCharge_list and len(userID_inCharge_list) > 0:
            notion_user_id = userID_inCharge_list[0].get("id")

        parsed_tasks[task.get("id")] = {
            "name": name,
            "status": status,
            "due_date": due_date,
            "project": project,
            "notion_user_id": notion_user_id,
        }

    return parsed_tasks


project_id_type = NewType("project_id_type", str)
project_map_type = dict[project_id_type, Any]


def get_active_projects() -> project_map_type:
    """
    Get all projects from the projects database
    """
    notion_client: Client = NotionClient()
    response: Any = notion_client.databases.query(
        database_id=NOTION_PRODUCTION_DATABASE_ID_PROJECTS,
        # TODO filter based on active
        filter={
            "or": [
                {"property": "Progress", "select": {"does_not_equal": "Archive"}},
                {"property": "Progress", "select": {"does_not_equal": "Cancelled"}},
                {"property": "Progress", "select": {"does_not_equal": "Finished"}},
            ]
        },
    )

    projects: list[dict[str, Any]] = response.get("results", [])
    parsed_projects: project_map_type = {}
    for project in projects:
        name: Optional[Any] = None
        name_prop: Any = project.get("properties", {}).get("Name", {})
        title_list: list[Any] = name_prop.get("title", [])
        if title_list and len(title_list) > 0:
            text_obj = title_list[0].get("text", {})
            name = text_obj.get("content")

        project_id: Optional[project_id_type] = project_id_type(project.get("id", None))
        assert project_id is not None
        parsed_projects[project_id] = name

    return parsed_projects


def create_task(
    task_name: str,
    user_id: str,  # TODO change to a list
    due_date: Optional[str] = None,
    notion_project_id: Optional[str] = None,
    # TODO add more
) -> Any:
    """
    Create a new task in the tasks database

    Args:
        task_name: The name of the task
        due_date: The due date of the task
        user_id: The user ID of the person in charge of the task
        notion_project_id: The ID of the project the task is associated with (need to call get_active_projects to get the list of projects and their ids)

    Returns:
        str: Success or failure of the creation
    """
    properties: dict[str, Any] = {
        "Name": {"title": [{"text": {"content": task_name}}]},
        "In Charge": {"people": [{"object": "user", "id": user_id}]},
    }
    if due_date:
        properties["Due Dates"] = {"date": {"start": due_date}}
    if notion_project_id:
        properties["Event/Project"] = {"relation": [{"id": notion_project_id}]}

    notion_client: Client = NotionClient()
    response: Any = notion_client.pages.create(
        parent={"database_id": NOTION_PRODUCTION_DATABASE_ID_TASKS},
        properties=properties,
    )
    return response


def update_task(
    notion_task_id: str,
    task_name: Optional[str] = None,
    task_status: Optional[
        Literal["Not Started", "In Progress", "Blocked", "To Review", "Done", "Archive"]
    ] = None,  # TODO should maybe make a property?
    task_due_date: Optional[str] = None,
    task_in_charge: Optional[list[Any]] = None,  # TODO define type
    task_event_project: Optional[str] = None,
) -> Any:
    """
    Update a task in the tasks database

    Args:
        notion_task_id: The ID of the task to update
        task_name: The name of the task
        task_status: The status of the task (to label a task as finished or completed, use Done word)
        task_due_date: The due date of the task ISO 8601 with timezone (we are in AEST)
        task_in_charge: The user of the person in charge of the task
        task_event_project: The ID of the project the task is associated with (need to call get_active_projects to get the list of projects and their ids)

    Returns:
        Success or failure of the update
    """
    properties = {}
    print("HELLO I AM HERE")
    if task_name:
        properties["Name"] = {"title": [{"text": {"content": task_name}}]}

    if task_status:
        properties["Status"] = {"status": {"name": task_status}}

    if task_due_date:
        print("HELLO I AM HERE 2")
        date = datetime.fromisoformat(task_due_date)
        properties["Due Dates"] = {"date": {"start": date}}
        print("HELLO I AM HERE 3")

    if task_in_charge:
        first_user = task_in_charge[0]

        properties["In Charge"] = {
            "people": [{"object": "user", "id": first_user.notion_id}]
        }  # TODO update

    if task_event_project:
        properties["Event/Project"] = {"relation": {"contains": task_event_project}}

    notion_client: Client = NotionClient()
    response: Any = notion_client.pages.update(
        page_id=notion_task_id,
        properties=properties,
    )

    print(response)
    return response


if __name__ == "__main__":
    import time
    from pprint import pprint

    start_time = time.time()
    # tasks = get_active_tasks()
    # pprint(tasks)
    pprint(get_all_users())
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    
    # start_time = time.time()
    # projects = get_active_projects()
    # pprint(projects)
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")

    # start_time = time.time()
    # response = create_task(
    #     task_name="Test Task",
    #     due_date=date(2024, 1, 1),
    #     user_id="f746733c-66cc-4cbc-b553-c5d3f03ed240",
    #     notion_project_id="168c2e93-a412-801e-9400-c4903f10a7a5",
    # )
    # pprint(response)
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")

    # start_time = time.time()
    # response = update_task(
    #     notion_task_id="1cbc2e93-a412-8112-906a-cf4115b04702",
    #     task_status="Done",
    # )
    # pprint(response)
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")

    # start_time = time.time()
    # pprint(get_all_users())
    # end_time = time.time()
    # print(f"Time taken: {end_time - start_time} seconds")
