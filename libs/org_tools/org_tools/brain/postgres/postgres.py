import os
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class DatabaseEngine:
    _engine: Optional[Engine] = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            # Load environment and create engine
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / ".env"
            load_dotenv()
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL is not set.")
            cls._engine = create_engine(database_url)
        return cls._engine

def get_user(discord_id: str) -> Optional[dict[str, Any]]:
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT *
        FROM gold.users_base
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id})
        user = result.mappings().first()
        return dict(user) if user else None


def get_user_fact(discord_id: str, days_back: int = 30) -> list[dict[str, Any]]:
    engine = DatabaseEngine.get_engine()
    days_ago = datetime.now() - timedelta(days=days_back)
    query = text("""
        SELECT f.*
        FROM gold.all_facts f
        JOIN gold.users_base u ON f.user_name = u.name
        WHERE u.discord_id = :discord_id
          AND f.created_at >= :days_ago
        ORDER BY f.created_at DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id, "days_ago": days_ago})
        facts = result.mappings().all()
        return [dict(fact) for fact in facts]


def set_user_fact(discord_id: str, fact_text: str) -> None:
    engine = DatabaseEngine.get_engine()
    user_query = text("""
        SELECT id
        FROM silver.user
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.begin() as conn:
        user_result = conn.execute(user_query, {"discord_id": discord_id})
        user = user_result.fetchone()
        if not user:
            raise ValueError(f"No user found with discord_id {discord_id}")
        user_id = user.id
        insert_query = text("""
            INSERT INTO silver.fact (user_id, fact_text)
            VALUES (:user_id, :fact_text)
        """)
        conn.execute(insert_query, {"user_id": user_id, "fact_text": fact_text})
        print(f"✅ Inserted fact for user {discord_id}")


def get_user_facts_with_keywords(
    discord_id: str, keywords: list[str]
) -> list[dict[str, Any]]:
    engine = DatabaseEngine.get_engine()
    processed_keywords = [f"%{keyword}%" for keyword in keywords]
    query = text("""
        SELECT f.*
        FROM gold.all_facts f
        JOIN gold.users_base u ON f.user_name = u.name
        WHERE u.discord_id = :discord_id AND f.fact_text LIKE ANY(:keywords)
        ORDER BY f.created_at DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(
            query, {"discord_id": discord_id, "keywords": processed_keywords}
        )
        facts = result.mappings().all()
        return [dict(fact) for fact in facts]


def delete_fact(discord_id: str, fact_id: str) -> None:
    engine = DatabaseEngine.get_engine()
    user_query = text("""
        SELECT id
        FROM silver.user
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.begin() as conn:
        user_result = conn.execute(user_query, {"discord_id": discord_id})
        user = user_result.fetchone()
        if not user:
            raise ValueError(f"No user found with discord_id {discord_id}")
        user_id = user.id
        delete_query = text("""
            DELETE FROM silver.fact
            WHERE fact_id = :fact_id AND user_id = :user_id
        """)
        conn.execute(delete_query, {"user_id": user_id, "fact_id": int(fact_id)})
        print(f"✅ Deleted fact for user {discord_id}")


def set_initial_committee_personal_checkup() -> None:
    """
    Initialize committee personal checkup rows for each committee member.
    Only inserts rows for members who don't already have an active checkup record.
    This function is designed to test the SCD2 design without truncating existing data.
    """
    engine = DatabaseEngine.get_engine()

    # Query to find committee members who don't have active checkup records
    query = text("""
        INSERT INTO silver.committee_personal_checkup 
        (member_id, committee_name, personal_description, checkup_text, start_date, end_date, is_current)
        SELECT 
            c.member_id,
            c.name,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            '9999-12-31',
            TRUE
        FROM silver.committee c
        WHERE NOT EXISTS (
            SELECT 1 
            FROM silver.committee_personal_checkup cpc 
            WHERE cpc.member_id = c.member_id 
            AND cpc.is_current = TRUE
        )
    """)

    with engine.begin() as conn:
        result = conn.execute(query)
        inserted_count = result.rowcount
        print(f"✅ Initialized {inserted_count} committee personal checkup records")

        if inserted_count == 0:
            print("ℹ️  All committee members already have active checkup records")


def set_committee_personal_checkup(
    discord_id: str, checkup_text: str, start_date: datetime
) -> None:
    """
    Add a new checkup row for a committee member identified by discord_id.
    This function follows SCD2 pattern by ending the current active record and creating a new one.

    Args:
        discord_id: Discord ID of the committee member
        checkup_text: The checkup text to add
        start_date: Start date for the new checkup record
    """
    engine = DatabaseEngine.get_engine()

    # First, find the member_id for the given discord_id
    committee_query = text("""
        SELECT member_id, name
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)

    with engine.begin() as conn:
        # Get committee info
        committee_result = conn.execute(committee_query, {"discord_id": discord_id})
        committee = committee_result.fetchone()

        if not committee:
            raise ValueError(f"No committee member found with discord_id {discord_id}")

        member_id = committee.member_id
        committee_name = committee.name

        # End the current active record (if it exists)
        end_current_query = text("""
            UPDATE silver.committee_personal_checkup
            SET end_date = :start_date, is_current = FALSE
            WHERE member_id = :member_id 
            AND is_current = TRUE
        """)

        end_result = conn.execute(
            end_current_query, {"member_id": member_id, "start_date": start_date}
        )

        # Get the personal_description from the current active record (if it exists)
        personal_desc_query = text("""
            SELECT personal_description
            FROM silver.committee_personal_checkup
            WHERE member_id = :member_id AND is_current = TRUE
            LIMIT 1
        """)

        personal_desc_result = conn.execute(
            personal_desc_query, {"member_id": member_id}
        )
        personal_desc_row = personal_desc_result.fetchone()
        personal_description = (
            personal_desc_row.personal_description if personal_desc_row else None
        )

        # Insert the new checkup record
        insert_query = text("""
            INSERT INTO silver.committee_personal_checkup 
            (member_id, committee_name, personal_description, checkup_text, start_date, end_date, is_current)
            VALUES (:member_id, :committee_name, :personal_description, :checkup_text, :start_date, '9999-12-31', TRUE)
        """)

        conn.execute(
            insert_query,
            {
                "member_id": member_id,
                "committee_name": committee_name,
                "personal_description": personal_description,
                "checkup_text": checkup_text,
                "start_date": start_date,
            },
        )

        print(
            f"✅ Added checkup for committee member {committee_name} (ID: {member_id})"
        )
        if end_result.rowcount > 0:
            print(f"   Ended previous active record and created new one")
        else:
            print(f"   Created first checkup record for this member")


def get_latest_personal_checkup(discord_id: str) -> str:
    """
    Fetch the most recent personal checkup row for a given discord_id.
    Returns a formatted string with the personal description and latest checkup for LLM consumption.
    """
    engine = DatabaseEngine.get_engine()
    committee_query = text("""
        SELECT member_id, name
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        committee_result = conn.execute(committee_query, {"discord_id": discord_id})
        committee = committee_result.fetchone()
        if not committee:
            return f"No committee member found for discord_id {discord_id}."
        member_id = committee.member_id
        committee_name = committee.name
        checkup_query = text("""
            SELECT personal_description, checkup_text, start_date
            FROM silver.committee_personal_checkup
            WHERE member_id = :member_id
            ORDER BY is_current DESC, start_date DESC
            LIMIT 1
        """)
        checkup = conn.execute(checkup_query, {"member_id": member_id}).fetchone()
        if not checkup:
            return f"No checkup records found for committee member '{committee_name}'."
        personal_desc = checkup.personal_description or "(No personal description)"
        checkup_text = checkup.checkup_text or "(No checkup text)"
        start_date = (
            checkup.start_date.strftime("%Y-%m-%d")
            if checkup.start_date
            else "(No date)"
        )
        return (
            f"Committee Member: {committee_name}\n"
            f"Latest Checkup Date: {start_date}\n"
            f"Personal Description: {personal_desc}\n"
            f"Checkup: {checkup_text}"
        )


def get_checkups_for_discord_id(
    discord_id: str, as_of: Optional[datetime] = None
) -> dict[str, Any]:
    """
    Fetch all checkups for a discord_id, or as of a particular datetime if provided.
    Returns a dictionary with the latest personal description and all relevant checkups with their dates.
    """
    engine = DatabaseEngine.get_engine()
    committee_query = text("""
        SELECT member_id, name
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        committee_result = conn.execute(committee_query, {"discord_id": discord_id})
        committee = committee_result.fetchone()
        if not committee:
            return {"error": f"No committee member found for discord_id {discord_id}."}
        member_id = committee.member_id
        committee_name = committee.name
        if as_of:
            checkup_query = text("""
                SELECT personal_description, checkup_text, start_date
                FROM silver.committee_personal_checkup
                WHERE member_id = :member_id AND start_date <= :as_of
                ORDER BY start_date DESC
            """)
            checkups = conn.execute(
                checkup_query, {"member_id": member_id, "as_of": as_of}
            ).fetchall()
        else:
            checkup_query = text("""
                SELECT personal_description, checkup_text, start_date
                FROM silver.committee_personal_checkup
                WHERE member_id = :member_id
                ORDER BY start_date DESC
            """)
            checkups = conn.execute(checkup_query, {"member_id": member_id}).fetchall()
        if not checkups:
            return {
                "committee_member": committee_name,
                "personal_description": "(No personal description)",
                "checkups": [],
                "last_checkup": "(No checkup records found)",
            }
        # Use the latest personal description (from the first record since we ordered DESC)
        latest_personal_desc = (
            checkups[0].personal_description or "(No personal description)"
        )
        checkup_list = []
        for checkup in checkups:
            date_str = (
                checkup.start_date.strftime("%Y-%m-%d")
                if checkup.start_date
                else "(No date)"
            )
            checkup_text = checkup.checkup_text or "(No checkup text)"
            checkup_list.append({"date": date_str, "text": checkup_text}) # type: ignore

        return {
            "committee_member": committee_name,
            "personal_description": latest_personal_desc,
            "checkups": checkup_list,
            "last_checkup": checkup_list[0]["text"]
            if checkup_list
            else "(No checkup records found)",
        }


def get_current_personal_description(discord_id: str) -> str:
    """
    Fetch the current personal description for a given discord_id.
    Returns the personal description from the most recent checkup record.
    """
    engine = DatabaseEngine.get_engine()
    committee_query = text("""
        SELECT member_id, name
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        committee_result = conn.execute(committee_query, {"discord_id": discord_id})
        committee = committee_result.fetchone()
        if not committee:
            return f"No committee member found for discord_id {discord_id}."

        member_id = committee.member_id

        checkup_query = text("""
            SELECT personal_description
            FROM silver.committee_personal_checkup
            WHERE member_id = :member_id
            ORDER BY is_current DESC, start_date DESC
            LIMIT 1
        """)
        checkup = conn.execute(checkup_query, {"member_id": member_id}).fetchone()

        if not checkup:
            return "(No personal description available)"

        return checkup.personal_description or "(No personal description)"


def set_personal_description(discord_id: str, personal_description: str) -> None:
    """
    Update the personal_description of the latest (active) row for a given discord_id.
    This function does not create a new SCD2 record - it just updates the existing active record.

    Args:
        discord_id: Discord ID of the committee member
        personal_description: The new personal description to set
    """
    engine = DatabaseEngine.get_engine()

    # First, find the member_id for the given discord_id
    committee_query = text("""
        SELECT member_id, name
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)

    with engine.begin() as conn:
        # Get committee info
        committee_result = conn.execute(committee_query, {"discord_id": discord_id})
        committee = committee_result.fetchone()

        if not committee:
            raise ValueError(f"No committee member found with discord_id {discord_id}")

        member_id = committee.member_id
        committee_name = committee.name

        # Update the personal_description of the current active record
        update_query = text("""
            UPDATE silver.committee_personal_checkup
            SET personal_description = :personal_description
            WHERE member_id = :member_id 
            AND is_current = TRUE
        """)

        result = conn.execute(
            update_query,
            {"member_id": member_id, "personal_description": personal_description},
        )

        if result.rowcount == 0:
            raise ValueError(
                f"No active checkup record found for committee member {committee_name}"
            )

        print(
            f"✅ Updated personal description for committee member {committee_name} (ID: {member_id})"
        )
        print(f"   New description: {personal_description}")


def get_committee_member_by_notion_id(notion_id: str) -> Optional[dict[str, Any]]:
    """
    Retrieve a committee member by their Notion ID.

    Args:
        notion_id: The Notion ID of the committee member

    Returns:
        Dictionary containing member data or None if not found
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT member_id, name, notion_id, discord_id, discord_dm_channel_id, ingestion_timestamp
        FROM silver.committee
        WHERE notion_id = :notion_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"notion_id": notion_id})
        member = result.mappings().first()
        return dict(member) if member else None


def get_committee_member_by_discord_id(discord_id: str) -> Optional[dict[str, Any]]:
    """
    Retrieve a committee member by their Discord ID.

    Args:
        discord_id: The Discord ID of the committee member

    Returns:
        Dictionary containing member data or None if not found
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT member_id, name, notion_id, discord_id, discord_dm_channel_id, ingestion_timestamp
        FROM silver.committee
        WHERE discord_id = :discord_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id})
        member = result.mappings().first()
        return dict(member) if member else None


def get_committee_member_by_discord_dm_channel_id(
    discord_dm_channel_id: int,
) -> Optional[dict[str, Any]]:
    """
    Retrieve a committee member by their Discord DM channel ID.

    Args:
        discord_dm_channel_id: The Discord DM channel ID of the committee member

    Returns:
        Dictionary containing member data or None if not found
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT member_id, name, notion_id, discord_id, discord_dm_channel_id, ingestion_timestamp
        FROM silver.committee
        WHERE discord_dm_channel_id = :discord_dm_channel_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_dm_channel_id": discord_dm_channel_id})
        member = result.mappings().first()
        return dict(member) if member else None


def get_meetings_by_discord_id(discord_id: int) -> list[dict[str, Any]]:
    """
    Get all meetings a Discord user participated in.

    Args:
        discord_id: The Discord ID of the user

    Returns:
        List of dictionaries containing meeting data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT DISTINCT m.name as meeting_name, m.type, m.meeting_timestamp
        FROM silver.meeting m
        JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
        JOIN silver.committee c ON mm.member_id = c.member_id
        WHERE c.discord_id = :discord_id
        ORDER BY m.meeting_timestamp DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id})
        meetings = result.mappings().all()
        return [dict(meeting) for meeting in meetings]


def get_projects_by_discord_id(discord_id: int) -> list[dict[str, Any]]:
    """
    Get all projects a Discord user is involved in.

    Args:
        discord_id: The Discord ID of the user

    Returns:
        List of dictionaries containing project data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT p.project_name, pm.ingestion_timestamp
        FROM silver.committee c
        JOIN silver.project_members pm ON c.member_id = pm.member_id
        JOIN silver.project p ON pm.project_id = p.project_id
        WHERE c.discord_id = :discord_id
        ORDER BY p.project_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id})
        projects = result.mappings().all()
        return [dict(project) for project in projects]


def get_projects_by_member_name(member_name: str) -> list[dict[str, Any]]:
    """
    Get all projects a committee member is involved in.

    Args:
        member_name: The name of the committee member

    Returns:
        List of dictionaries containing project data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT p.project_name, pm.ingestion_timestamp
        FROM silver.committee c
        JOIN silver.project_members pm ON c.member_id = pm.member_id
        JOIN silver.project p ON pm.project_id = p.project_id
        WHERE c.name = :member_name
        ORDER BY p.project_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"member_name": member_name})
        projects = result.mappings().all()
        return [dict(project) for project in projects]


def get_participants_by_meeting_name(meeting_name: str) -> list[dict[str, Any]]:
    """
    Get all participants in a specific meeting.

    Args:
        meeting_name: The name of the meeting

    Returns:
        List of dictionaries containing participant data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT c.name as member_name, c.discord_id, c.notion_id, mm.type as participation_type
        FROM silver.meeting m
        JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
        JOIN silver.committee c ON mm.member_id = c.member_id
        WHERE m.name = :meeting_name
        ORDER BY c.name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"meeting_name": meeting_name})
        participants = result.mappings().all()
        return [dict(participant) for participant in participants]


def get_projects_by_meeting_name(meeting_name: str) -> list[dict[str, Any]]:
    """
    Get all projects discussed in a specific meeting.

    Args:
        meeting_name: The name of the meeting

    Returns:
        List of dictionaries containing project data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT p.project_name, mp.ingestion_timestamp
        FROM silver.meeting m
        JOIN silver.meeting_projects mp ON m.meeting_id = mp.meeting_id
        JOIN silver.project p ON mp.project_id = p.project_id
        WHERE m.name = :meeting_name
        ORDER BY p.project_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"meeting_name": meeting_name})
        projects = result.mappings().all()
        return [dict(project) for project in projects]


def get_meetings_by_notion_id(notion_id: str) -> list[dict[str, Any]]:
    """
    Get all meetings a Notion user participated in.

    Args:
        notion_id: The Notion ID of the user

    Returns:
        List of dictionaries containing meeting data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT DISTINCT m.name as meeting_name, m.type, m.meeting_timestamp
        FROM silver.meeting m
        JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
        JOIN silver.committee c ON mm.member_id = c.member_id
        WHERE c.notion_id = :notion_id
        ORDER BY m.meeting_timestamp DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"notion_id": notion_id})
        meetings = result.mappings().all()
        return [dict(meeting) for meeting in meetings]


def get_meetings_by_project_name(project_name: str) -> list[dict[str, Any]]:
    """
    Get all meetings related to a specific project.

    Args:
        project_name: The name of the project

    Returns:
        List of dictionaries containing meeting data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT m.name as meeting_name, m.type, m.meeting_timestamp, m.meeting_summary
        FROM silver.project p
        JOIN silver.meeting_projects mp ON p.project_id = mp.project_id
        JOIN silver.meeting m ON mp.meeting_id = m.meeting_id
        WHERE p.project_name = :project_name
        ORDER BY m.meeting_timestamp DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"project_name": project_name})
        meetings = result.mappings().all()
        return [dict(meeting) for meeting in meetings]


def get_members_by_project_name(project_name: str) -> list[dict[str, Any]]:
    """
    Get all committee members working on a specific project.

    Args:
        project_name: The name of the project

    Returns:
        List of dictionaries containing member data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT c.name as member_name, c.discord_id, c.notion_id, pm.ingestion_timestamp
        FROM silver.project p
        JOIN silver.project_members pm ON p.project_id = pm.project_id
        JOIN silver.committee c ON pm.member_id = c.member_id
        WHERE p.project_name = :project_name
        ORDER BY c.name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"project_name": project_name})
        members = result.mappings().all()
        return [dict(member) for member in members]


# === Topic-Related Functions ===
 
def get_all_topics() -> list[dict[str, Any]]:
    """
    Get all topics in the system.

    Returns:
        List of dictionaries containing topic data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT topic_id, topic_name, ingestion_timestamp
        FROM silver.topic
        ORDER BY topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_topics_by_keyword(keyword: str) -> list[dict[str, Any]]:
    """
    Search topics by keyword in the topic name.

    Args:
        keyword: The keyword to search for

    Returns:
        List of dictionaries containing matching topic data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT topic_id, topic_name, ingestion_timestamp
        FROM silver.topic
        WHERE topic_name ILIKE :keyword
        ORDER BY topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"keyword": f"%{keyword}%"})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_topics_by_meeting_id(meeting_id: int) -> list[dict[str, Any]]:
    """
    Get all topics for a meeting by ID.

    Args:
        meeting_id: The ID of the meeting

    Returns:
        List of dictionaries containing topic data with summaries
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT t.topic_id, t.topic_name, mt.topic_summary, mt.ingestion_timestamp
        FROM silver.meeting_topics mt
        JOIN silver.topic t ON mt.topic_id = t.topic_id
        WHERE mt.meeting_id = :meeting_id
        ORDER BY t.topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"meeting_id": meeting_id})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_meetings_by_topic_name(topic_name: str) -> list[dict[str, Any]]:
    """
    Get all meetings that discussed a specific topic.

    Args:
        topic_name: The name of the topic

    Returns:
        List of dictionaries containing meeting data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT m.meeting_id, m.name as meeting_name, m.type, m.meeting_timestamp, 
               mt.topic_summary, mt.ingestion_timestamp
        FROM silver.topic t
        JOIN silver.meeting_topics mt ON t.topic_id = mt.topic_id
        JOIN silver.meeting m ON mt.meeting_id = m.meeting_id
        WHERE t.topic_name = :topic_name
        ORDER BY m.meeting_timestamp DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"topic_name": topic_name})
        meetings = result.mappings().all()
        return [dict(meeting) for meeting in meetings]


def get_meetings_by_topic_id(topic_id: int) -> list[dict[str, Any]]:
    """
    Get all meetings for a topic by ID.

    Args:
        topic_id: The ID of the topic

    Returns:
        List of dictionaries containing meeting data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT m.meeting_id, m.name as meeting_name, m.type, m.meeting_timestamp, 
               mt.topic_summary, mt.ingestion_timestamp
        FROM silver.meeting_topics mt
        JOIN silver.meeting m ON mt.meeting_id = m.meeting_id
        WHERE mt.topic_id = :topic_id
        ORDER BY m.meeting_timestamp DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"topic_id": topic_id})
        meetings = result.mappings().all()
        return [dict(meeting) for meeting in meetings]


def get_meeting_with_topics(meeting_name: str) -> Optional[dict[str, Any]]:
    """
    Get meeting details including all topics and their summaries.

    Args:
        meeting_name: The name of the meeting

    Returns:
        Dictionary containing meeting data with topics list or None if not found
    """
    engine = DatabaseEngine.get_engine()
    meeting_query = text("""
        SELECT meeting_id, name, type, meeting_summary, meeting_timestamp, ingestion_timestamp
        FROM silver.meeting
        WHERE name = :meeting_name
        LIMIT 1
    """)
    topics_query = text("""
        SELECT t.topic_id, t.topic_name, mt.topic_summary
        FROM silver.meeting_topics mt
        JOIN silver.topic t ON mt.topic_id = t.topic_id
        WHERE mt.meeting_id = :meeting_id
        ORDER BY t.topic_name
    """)
    with engine.connect() as conn:
        meeting_result = conn.execute(meeting_query, {"meeting_name": meeting_name})
        meeting = meeting_result.mappings().first()
        
        if not meeting:
            return None
        
        meeting_dict = dict(meeting)
        topics_result = conn.execute(topics_query, {"meeting_id": meeting_dict["meeting_id"]})
        topics = [dict(topic) for topic in topics_result.mappings().all()]
        meeting_dict["topics"] = topics
        
        return meeting_dict


def get_meeting_with_topics_by_id(meeting_id: int) -> Optional[dict[str, Any]]:
    """
    Get meeting details by ID including topics.

    Args:
        meeting_id: The ID of the meeting

    Returns:
        Dictionary containing meeting data with topics list or None if not found
    """
    engine = DatabaseEngine.get_engine()
    meeting_query = text("""
        SELECT meeting_id, name, type, meeting_summary, meeting_timestamp, ingestion_timestamp
        FROM silver.meeting
        WHERE meeting_id = :meeting_id
        LIMIT 1
    """)
    topics_query = text("""
        SELECT t.topic_id, t.topic_name, mt.topic_summary
        FROM silver.meeting_topics mt
        JOIN silver.topic t ON mt.topic_id = t.topic_id
        WHERE mt.meeting_id = :meeting_id
        ORDER BY t.topic_name
    """)
    with engine.connect() as conn:
        meeting_result = conn.execute(meeting_query, {"meeting_id": meeting_id})
        meeting = meeting_result.mappings().first()
        
        if not meeting:
            return None
        
        meeting_dict = dict(meeting)
        topics_result = conn.execute(topics_query, {"meeting_id": meeting_id})
        topics = [dict(topic) for topic in topics_result.mappings().all()]
        meeting_dict["topics"] = topics
        
        return meeting_dict


def get_topic_summary_by_meeting_and_topic(meeting_name: str, topic_name: str) -> Optional[str]:
    """
    Get the specific summary of how a topic was discussed in a meeting.

    Args:
        meeting_name: The name of the meeting
        topic_name: The name of the topic

    Returns:
        Topic summary string or None if not found
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT mt.topic_summary
        FROM silver.meeting m
        JOIN silver.meeting_topics mt ON m.meeting_id = mt.meeting_id
        JOIN silver.topic t ON mt.topic_id = t.topic_id
        WHERE m.name = :meeting_name AND t.topic_name = :topic_name
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"meeting_name": meeting_name, "topic_name": topic_name})
        row = result.fetchone()
        return row[0] if row else None


def get_topics_by_date_range(start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
    """
    Get topics discussed within a date range.

    Args:
        start_date: Start date for the range
        end_date: End date for the range

    Returns:
        List of dictionaries containing topic data with meeting information
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT DISTINCT t.topic_id, t.topic_name, m.name as meeting_name, 
               m.meeting_timestamp, mt.topic_summary
        FROM silver.topic t
        JOIN silver.meeting_topics mt ON t.topic_id = mt.topic_id
        JOIN silver.meeting m ON mt.meeting_id = m.meeting_id
        WHERE m.meeting_timestamp >= :start_date AND m.meeting_timestamp <= :end_date
        ORDER BY m.meeting_timestamp DESC, t.topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"start_date": start_date, "end_date": end_date})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_most_discussed_topics(limit: int = 10) -> list[dict[str, Any]]:
    """
    Get the most frequently discussed topics.

    Args:
        limit: Maximum number of topics to return (default: 10)

    Returns:
        List of dictionaries containing topic data with discussion count
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT t.topic_id, t.topic_name, COUNT(mt.meeting_id) as discussion_count
        FROM silver.topic t
        JOIN silver.meeting_topics mt ON t.topic_id = mt.topic_id
        GROUP BY t.topic_id, t.topic_name
        ORDER BY discussion_count DESC, t.topic_name
        LIMIT :limit
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": limit})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_topics_by_project_name(project_name: str) -> list[dict[str, Any]]:
    """
    Get topics related to a specific project (topics discussed in meetings where the project was mentioned).

    Args:
        project_name: The name of the project

    Returns:
        List of dictionaries containing topic data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT DISTINCT t.topic_id, t.topic_name, COUNT(mt.meeting_id) as discussion_count
        FROM silver.topic t
        JOIN silver.meeting_topics mt ON t.topic_id = mt.topic_id
        JOIN silver.meeting m ON mt.meeting_id = m.meeting_id
        JOIN silver.meeting_projects mp ON m.meeting_id = mp.meeting_id
        JOIN silver.project p ON mp.project_id = p.project_id
        WHERE p.project_name = :project_name
        GROUP BY t.topic_id, t.topic_name
        ORDER BY discussion_count DESC, t.topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"project_name": project_name})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def get_topics_by_member_name(member_name: str) -> list[dict[str, Any]]:
    """
    Get topics that a specific member has been involved in discussing.

    Args:
        member_name: The name of the committee member

    Returns:
        List of dictionaries containing topic data
    """
    engine = DatabaseEngine.get_engine()
    query = text("""
        SELECT DISTINCT t.topic_id, t.topic_name, COUNT(mt.meeting_id) as discussion_count
        FROM silver.topic t
        JOIN silver.meeting_topics mt ON t.topic_id = mt.topic_id
        JOIN silver.meeting m ON mt.meeting_id = m.meeting_id
        JOIN silver.meeting_members mm ON m.meeting_id = mm.meeting_id
        JOIN silver.committee c ON mm.member_id = c.member_id
        WHERE c.name = :member_name
        GROUP BY t.topic_id, t.topic_name
        ORDER BY discussion_count DESC, t.topic_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"member_name": member_name})
        topics = result.mappings().all()
        return [dict(topic) for topic in topics]


def main():
    try:
        # Test the new topic functions
        print("Testing topic functions...")
        
        # Test getting all topics
        all_topics = get_all_topics()
        print(f"Found {len(all_topics)} topics in the system")
        
        # Test getting topics by keyword
        ai_topics = get_topics_by_keyword("AI")
        print(f"Found {len(ai_topics)} topics containing 'AI'")
        
        # Test getting most discussed topics
        popular_topics = get_most_discussed_topics(limit=5)
        print(f"Top 5 most discussed topics:")
        for topic in popular_topics:
            print(f"  - {topic['topic_name']} (discussed {topic['discussion_count']} times)")
            
    except ValueError as e:
        if "DATABASE_URL is not set" in str(e):
            print("❌ Error: DATABASE_URL environment variable is not set.")
            print("Please create a .env file in the project root with your database connection string.")
            print("Example: DATABASE_URL=postgresql://user:password@localhost:5432/database_name")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Make sure your database is running and accessible.")


if __name__ == "__main__":
    main()
