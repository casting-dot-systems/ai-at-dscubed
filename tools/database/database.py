import os
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine


class DatabaseEngine:
    _engine: Engine = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            # Load environment and create engine
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / '.env'
            load_dotenv(dotenv_path=env_path, override=True)
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL is not set.")
            cls._engine = create_engine(database_url)
        return cls._engine


def get_user(discord_id: str, engine: Engine = None) -> Optional[dict[str, Any]]:
    engine = engine or DatabaseEngine.get_engine()
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


def get_user_fact(discord_id: str, days_back: int = 30, engine: Engine = None) -> list[dict[str, Any]]:
    engine = engine or DatabaseEngine.get_engine()
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


def set_user_fact(discord_id: str, fact_text: str, engine: Engine = None) -> None:
    engine = engine or DatabaseEngine.get_engine()
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


def get_user_facts_with_keywords(discord_id: str, keywords: list[str], engine: Engine = None) -> list[dict[str, Any]]:
    engine = engine or DatabaseEngine.get_engine()
    processed_keywords = [f"%{keyword}%" for keyword in keywords]
    query = text("""
        SELECT f.*
        FROM gold.all_facts f
        JOIN gold.users_base u ON f.user_name = u.name
        WHERE u.discord_id = :discord_id AND f.fact_text ILIKE ANY(:keywords)
        ORDER BY f.created_at DESC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"discord_id": discord_id, "keywords": processed_keywords})
        facts = result.mappings().all()
        return [dict(fact) for fact in facts]


def delete_fact(discord_id: str, fact_id: str, engine: Engine = None) -> None:
    engine = engine or DatabaseEngine.get_engine()
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


