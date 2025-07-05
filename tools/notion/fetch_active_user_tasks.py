from tools.notion.notion_functions import get_active_tasks, get_active_projects

"""
INPUT: notion_user_id
OUTPUT: tuple of (list of task dictionaries, list of project dictionaries)

task dictionary:
- Task ID
- Task Name
- Task Due Date
- Task Progress
- Task Description
- Task Project ID

project dictionary:
- Project ID
- Project Name
- Project Description

"""


def get_task_and_project_info(notion_user_id):
    user_tasks = get_active_tasks(notion_user_id=notion_user_id)
    all_projects = get_active_projects()

    # get projects that the user is currently working on
    user_projects = {}
    # for every project, check if the user has any tasks in it
    for project_id, project_name in all_projects.items():
        # for every user task, check if it is in this project
        for task_id, task_data in user_tasks.items():
            # if the task is in this project, add it to the user_projects dict
            if task_data.get("project") == project_id:
                user_projects[project_id] = project_name
                break

    # formatting to dict, appending to list
    task_list = []
    for task_id, task_data in user_tasks.items():
        task_list.append(
            {
                "Task ID": task_id,
                "Task Name": task_data.get("name", ""),
                "Task Due Date": task_data.get("due_date", ""),
                "Task Progress": task_data.get("status", ""),
                "Task Description": "",
                "Task Project ID": task_data.get("project", ""),
            }
        )

    unique_projects = []
    for project_id, project_name in user_projects.items():
        unique_projects.append(
            {
                "Project ID": project_id,
                "Project Name": project_name,
                "Project Description": "",
            }
        )

    # return as tuple
    user_info = (task_list, unique_projects)

    return user_info


# uncomment for local testing
if __name__ == "__main__":
    test_user_id = "f746733c-66cc-4cbc-b553-c5d3f03ed240"  # PJ's Notion ID
    result = get_task_and_project_info(test_user_id)

    # print(result)

    print("=== TASKS ===")
    for i, task in enumerate(result[0], 1):
        print(f"Task {i}: {task}")

    print("\n=== PROJECTS ===")
    for i, project in enumerate(result[1], 1):
        print(f"Project {i}: {project}")

    print(f"\nTotal tasks: {len(result[0])}")
    print(f"Total projects: {len(result[1])}")
