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
            load_dotenv(dotenv_path=env_path, override=True)
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
            checkup_list.append({"date": date_str, "text": checkup_text})

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


def main():
    print(get_committee_member_by_discord_id("241085495398891521"))


if __name__ == "__main__":
    main()
