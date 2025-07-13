"""
This module contains the functions for the group functions.

The group functions are used to create, get, delete, and modify groups.
"""

from sqlalchemy import text
from custom_tools.brain.postgres.postgres import DatabaseEngine

class GroupFunctions:
    def __init__(self):
        self.engine = DatabaseEngine.get_engine()
    
    def create_group(
            self,
            group_name: str,
            group_description: str,
    ):
        """
        Create a new group with the given name and description.

        Args:
            group_name: The name of the group to create.
            group_description: A short description of the group.

        Returns:
            None if the group already exists, otherwise returns the group id.
        """
        engine = DatabaseEngine.get_engine()

        check_exisiting = text("""
            SELECT group_id FROM silver.group_table
            WHERE group_name = :group_name
        """)

        with engine.begin() as conn:
            result = conn.execute(check_exisiting, {"group_name": group_name})
            existing_group = result.fetchone()
            if existing_group:
                print(f"{group_name} already exists")
                return None 
            
        query = text("""
            INSERT INTO silver.group_table (group_name, group_description)
            VALUES (:group_name, :group_description)
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {
                "group_name": group_name,
                "group_description": group_description,
            })

            print(f"{group_name} created successfully")
            
    def get_group(
            self, 
            group_id: str,
    ):
        """
        Get a group by group id.

        Args:
            group_id: The id of the group to get.
        """
        engine = DatabaseEngine.get_engine()

        query = text("""
            SELECT g.group_id, g.group_name, g.group_description, 
                   c.member_id, c.discord_id, c.notion_id, c.name  
            FROM silver.group_table AS g 
            JOIN silver.group_members AS gm ON g.group_id = gm.group_id
            JOIN silver.committee AS c ON gm.user_id = c.member_id
            WHERE g.group_id = :group_id
        """)
        
        with engine.begin() as conn:
            result = conn.execute(query, {"group_id": group_id})
            rows = result.mappings().all()
            
            group_info = {
                "group_id": rows[0].group_id,
                "group_name": rows[0].group_name,
                "group_description": rows[0].group_description,
                "members": [
                    {
                        "user_id": row.member_id,
                        "discord_id": row.discord_id,
                        "notion_id": row.notion_id,
                        "name": row.name,
                    }
                    for row in rows
                ],
            }
            
            return rows

    def delete_group(
            self, 
            group_id: str,
    ):
        """
        Delete a group by group id.

        Args:
            group_id: The id of the group to delete.
        """
        engine = DatabaseEngine.get_engine()

        delete_query = text("""
                DELETE FROM silver.group_table
                WHERE group_id = :group_id
            """)
       
        with engine.begin() as conn:
            conn.execute(delete_query, {"group_id": group_id})
            print(f"{group_id} deleted successfully")

    def modify_group(
            self, 
            group_id: int, 
            user_id: int,
            action: str, # add or remove
    ):
        """
        Add or remove users to a group by group name.
        
        Args:
            group_id: The id of the group to modify.
            user_id: The id of the user to add or remove.
            action: The action to perform. Must be 'add' or 'remove'.
        """
        engine = DatabaseEngine.get_engine()

        if action not in ["add", "remove"]:
            raise ValueError("Invalid action. Must be 'add' or 'remove'")
        
        check_query = text("""
            SELECT 1 
            FROM silver.group_members
            WHERE user_id = :user_id AND group_id = :group_id
        """)

        assign_query = text("""
            INSERT INTO silver.group_members (group_id, user_id)
            VALUES (:group_id, :user_id)
        """)

        remove_query = text("""
            DELETE FROM silver.group_members 
            WHERE user_id = :user_id AND group_id = :group_id
        """)
        
        with engine.begin() as conn:
            check_result = conn.execute(check_query, {"user_id": user_id, "group_id": group_id})
            result = check_result.fetchone()
            
            if action == "add":
                if result:
                    print(f"{user_id} already in {group_id}")
                    return
                else:
                    conn.execute(assign_query, {"group_id": group_id, "user_id": user_id})
                    print(f"{user_id} added to {group_id} successfully")

            elif action == "remove":
                if not result:
                    print(f"{user_id} not in {group_id}")
                    return
                else:
                    conn.execute(remove_query, {"user_id": user_id, "group_id": group_id})
                    print(f"{user_id} removed from {group_id} successfully")
    
    def get_all_groups(self):
        """
        Get all groups.
        """
        engine = DatabaseEngine.get_engine()
        query = text("""
            SELECT group_id, group_name, group_description
            FROM silver.group_table
        """)

        with engine.begin() as conn:
            result = conn.execute(query)
            rows = result.mappings().all()
            return rows

    def get_group_id(
            self, 
            group_name: str,
    ) -> int:
        """
        Get the group id by group name.

        Args:
            group_name: The name of the group to get the id of.

        Returns:
            The group id.
        """
        engine = DatabaseEngine.get_engine()
        query = text("""
            SELECT group_id 
            FROM silver.group_table
            WHERE group_name = :group_name
        """)

        with engine.begin() as conn:
            result = conn.execute(query, {"group_name": group_name})
            row = result.fetchone()
            if not row:
                raise ValueError(f"Group {group_name} not found")
            return row.group_id

    def get_user_id(
            self, 
            user_name: str,
    ) -> int:
        """
        Get the user id by user name.

        Args:
            user_name: The name of the user to get the id of.

        Returns:
            The user id.
        """
        engine = DatabaseEngine.get_engine()
        query = text("""
            SELECT member_id 
            FROM silver.committee
            WHERE name = :user_name
        """)

        with engine.begin() as conn:
            result = conn.execute(query, {"user_name": user_name})
            row = result.fetchone()
            if not row:
                raise ValueError(f"User {user_name} not found")
            return row.member_id


