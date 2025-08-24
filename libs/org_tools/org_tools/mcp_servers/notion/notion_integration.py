"""
Integration layer between MCP tools and notion_functions.py
This file handles the conversion between MCP tool calls and your existing Notion functions.
"""

from typing import Any, Dict, List, Optional

from org_tools.brain.notion.notion_functions import get_all_users, get_active_tasks, create_task, update_task


async def get_notion_users() -> str:
    """Get all users from Notion and format them for MCP response."""
    try:
        users = get_all_users()
        if not users:
            return "No users found in Notion."
        
        user_list = []
        for user in users:
            user_list.append(f"ID: {user['id']}, Name: {user['name']}")
        
        return "\n".join(user_list)
    except Exception as e:
        return f"Error fetching users: {str(e)}"


async def get_notion_active_tasks(
    notion_user_id: Optional[str] = None,
    notion_project_id: Optional[str] = None
) -> str:
    """Get active tasks from Notion and format them for MCP response."""
    try:
        tasks = get_active_tasks(notion_user_id, notion_project_id)
        if not tasks:
            return "No active tasks found."
        
        task_list = []
        for task_id, task_data in tasks.items():
            task_info = f"""
Task ID: {task_id}
Name: {task_data.get('name', 'N/A')}
Status: {task_data.get('status', 'N/A')}
Due Date: {task_data.get('due_date', 'N/A')}
Project: {task_data.get('project', 'N/A')}
Assigned To: {task_data.get('notion_user_id', 'N/A')}
---"""
            task_list.append(task_info)
        
        return "\n".join(task_list)
    except Exception as e:
        return f"Error fetching tasks: {str(e)}"


async def create_notion_task(
    task_name: str,
    user_id: str,
    due_date: Optional[str] = None,
    notion_project_id: Optional[str] = None
) -> str:
    """Create a new task in Notion and return formatted response."""
    try:
        response = create_task(task_name, user_id, due_date, notion_project_id)
        task_id = response.get('id', 'Unknown')
        return f"Task '{task_name}' created successfully. Task ID: {task_id}"
    except Exception as e:
        return f"Error creating task: {str(e)}"


async def update_notion_task_status(
    notion_task_id: str,
    task_status: str
) -> str:
    """Update the status of a Notion task and return formatted response."""
    try:
        response = update_task(notion_task_id, task_status=task_status)
        return f"Task {notion_task_id} status updated to {task_status} successfully."
    except Exception as e:
        return f"Error updating task status: {str(e)}" 