from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("notion")


@mcp.tool()
async def get_all_users() -> str:
    """Get all users from Notion.
    
    Returns:
        A formatted string containing all Notion users with their IDs and names.
    """
    try:
        # Import and use the integration layer
        from notion_integration import get_notion_users
        return await get_notion_users()
    except Exception as e:
        return f"Error fetching users: {str(e)}"

@mcp.tool()
async def get_active_tasks(
    notion_user_id: Optional[str] = None,
    notion_project_id: Optional[str] = None
) -> str:
    """Get active tasks from Notion database.
    
    Args:
        notion_user_id: Optional Notion user ID to filter tasks by assignee
        notion_project_id: Optional Notion project ID to filter tasks by project
        
    Returns:
        A formatted string containing all active tasks with their details.
    """
    try:
        # This would integrate with your notion_functions.py
        # For now, returning a placeholder
        return f"Active tasks for user {notion_user_id} and project {notion_project_id} - integrate with notion_functions.py"
    except Exception as e:
        return f"Error fetching tasks: {str(e)}"

@mcp.tool()
async def create_task(
    task_name: str,
    user_id: str,
    due_date: Optional[str] = None,
    notion_project_id: Optional[str] = None
) -> str:
    """Create a new task in Notion.
    
    Args:
        task_name: The name/title of the task
        user_id: The Notion user ID of the person assigned to the task
        due_date: Optional due date in ISO format (YYYY-MM-DD)
        notion_project_id: Optional Notion project ID to associate the task with
        
    Returns:
        A string indicating success or failure of task creation.
    """
    try:
        # This would integrate with your notion_functions.py
        # For now, returning a placeholder
        return f"Task '{task_name}' created for user {user_id} - integrate with notion_functions.py"
    except Exception as e:
        return f"Error creating task: {str(e)}"

@mcp.tool()
async def update_task_status(
    notion_task_id: str,
    task_status: str
) -> str:
    """Update the status of a Notion task.
    
    Args:
        notion_task_id: The Notion task ID to update
        task_status: The new status (Not Started, In Progress, Blocked, To Review, Done, Archive)
        
    Returns:
        A string indicating success or failure of the status update.
    """
    try:
        # This would integrate with your notion_functions.py
        # For now, returning a placeholder
        return f"Task {notion_task_id} status updated to {task_status} - integrate with notion_functions.py"
    except Exception as e:
        return f"Error updating task status: {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    print("Notion MCP Server started")
    mcp.run(transport='stdio')
    