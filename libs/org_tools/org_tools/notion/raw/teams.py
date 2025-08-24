from typing import Optional, List

from .types import (
    TeamID, EventProjectID, DocumentID, Person,
    Team, TeamProperties, TEAMS_DB_ID
)
from .client import (
    get_notion_client,
    format_people_for_notion, format_relation_for_notion,
    parse_people_from_notion, parse_relation_from_notion
)

class TeamCRUDError(Exception):
    """Exception for Teams CRUD operations"""
    pass

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
        raise TeamCRUDError(f"Failed to create team: {str(e)}")

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
        raise TeamCRUDError(f"Failed to get team: {str(e)}")

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
        raise TeamCRUDError(f"Failed to update team: {str(e)}")

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
        raise TeamCRUDError(f"Failed to delete team: {str(e)}")

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
        raise TeamCRUDError(f"Failed to query teams: {str(e)}")

if __name__ == "__main__":
    """Demo of Teams CRUD operations"""
    print("=== Teams CRUD Demo ===")
    
    try:
        # Create a new team
        print("\n1. Creating a new team...")
        team_id = create_team(
            name="Marketing Team Demo",
            cover=["marketing-team-logo.png"]
        )
        print(f"✅ Created team with ID: {team_id}")
        
        # Get the team
        print("\n2. Retrieving the team...")
        team = get_team(team_id)
        if team:
            print(f"✅ Retrieved team: {team.name}")
            print(f"   Cover files: {team.cover}")
            print(f"   Members: {len(team.person) if team.person else 0}")
            print(f"   Associated projects: {len(team.events_projects) if team.events_projects else 0}")
        
        # Update the team
        print("\n3. Updating team information...")
        update_success = update_team(
            team_id,
            cover=["marketing-team-logo.png", "team-banner.jpg"]
        )
        if update_success:
            print("✅ Updated team cover files")
        
        # Create another team
        print("\n4. Creating a development team...")
        dev_team_id = create_team(
            name="Development Team Demo",
            cover=["dev-team-logo.png"]
        )
        print(f"✅ Created development team with ID: {dev_team_id}")
        
        # Query teams
        print("\n5. Querying teams...")
        teams = query_teams(limit=10)
        print(f"✅ Found {len(teams)} teams")
        for t in teams:
            print(f"   - {t.name}")
            if t.person:
                print(f"     Members: {len(t.person)}")
            if t.events_projects:
                print(f"     Projects: {len(t.events_projects)}")
        
        # Update team with more details
        print("\n6. Adding more team details...")
        update_team(
            team_id,
            cover=["marketing-team-logo.png", "team-banner.jpg", "team-photo.jpg"]
        )
        print("✅ Updated team with additional cover files")
        
        # Get updated team
        print("\n7. Retrieving updated team...")
        updated_team = get_team(team_id)
        if updated_team:
            print(f"✅ Team '{updated_team.name}' now has {len(updated_team.cover)} cover files")
        
        # Create a specialized team
        print("\n8. Creating a specialized team...")
        design_team_id = create_team(
            name="Design Team Demo"
        )
        print(f"✅ Created design team with ID: {design_team_id}")
        
        # Query all teams to see the full list
        print("\n9. Final team roster...")
        all_teams = query_teams(limit=20)
        print(f"✅ Total teams found: {len(all_teams)}")
        demo_teams = [t for t in all_teams if "Demo" in t.name]
        print(f"✅ Demo teams created: {len(demo_teams)}")
        
        # Clean up - delete the demo teams
        print("\n10. Cleaning up demo teams...")
        delete_team(team_id)
        delete_team(dev_team_id)
        delete_team(design_team_id)
        print("✅ Demo teams archived")
        
    except TeamCRUDError as e:
        print(f"❌ Error during demo: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n=== Demo Complete ===")