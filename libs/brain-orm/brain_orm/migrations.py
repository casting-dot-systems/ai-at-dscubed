"""
Database migration utilities for brain-core.
"""

from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DatabaseManager


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize migration manager."""
        self.db = db_manager

    async def create_schemas(self) -> None:
        """Create the required database schemas."""
        async with self.db.session_scope() as session:
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS catalog"))
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS silver"))

    async def create_extensions(self) -> None:
        """Create required PostgreSQL extensions."""
        async with self.db.session_scope() as session:
            # Enable UUID generation functions
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    async def create_indexes(self) -> None:
        """Create additional indexes for performance."""
        async with self.db.session_scope() as session:
            # Member indexes (based on brain_v2 schema)
            await session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_members_org_email
                ON catalog.members (org_id, primary_email)
                WHERE primary_email IS NOT NULL
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_members_org
                ON catalog.members (org_id)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_members_org_status
                ON catalog.members (org_id, status)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_members_org_team
                ON catalog.members (org_id, team)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_members_org_fullname
                ON catalog.members (org_id, full_name text_pattern_ops)
            """))

            # Message indexes for better query performance
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_component_created
                ON silver.messages (component_id, created_at_ts DESC)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_author_created
                ON silver.messages (author_member_id, created_at_ts DESC)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_system_created
                ON silver.messages (system, created_at_ts DESC)
            """))

            # Component indexes
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_components_org_system
                ON silver.components (org_id, system)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_components_parent
                ON silver.components (parent_component_id)
                WHERE parent_component_id IS NOT NULL
            """))

    async def create_functions(self) -> None:
        """Create PostgreSQL functions for data processing."""
        async with self.db.session_scope() as session:
            # Function to ensure member exists for Discord user
            await session.execute(text("""
                CREATE OR REPLACE FUNCTION ensure_member_for_discord(
                    p_org_id TEXT,
                    p_discord_user_id TEXT,
                    p_display_name TEXT DEFAULT NULL,
                    p_email TEXT DEFAULT NULL
                ) RETURNS UUID AS $$
                DECLARE
                    v_member_id UUID;
                    v_existing_member_id UUID;
                BEGIN
                    -- Check if identity already exists
                    SELECT member_id INTO v_existing_member_id
                    FROM catalog.member_identities
                    WHERE system = 'discord' AND external_id = p_discord_user_id;

                    IF v_existing_member_id IS NOT NULL THEN
                        -- Update existing identity
                        UPDATE catalog.member_identities
                        SET display_name = COALESCE(p_display_name, display_name),
                            email = COALESCE(p_email, email),
                            updated_at = NOW()
                        WHERE system = 'discord' AND external_id = p_discord_user_id;

                        RETURN v_existing_member_id;
                    END IF;

                    -- Create new member
                    INSERT INTO catalog.members (org_id, preferred_name, primary_email)
                    VALUES (p_org_id, p_display_name, p_email)
                    RETURNING member_id INTO v_member_id;

                    -- Create identity
                    INSERT INTO catalog.member_identities (
                        member_id, system, external_id, display_name, email
                    ) VALUES (
                        v_member_id, 'discord', p_discord_user_id, p_display_name, p_email
                    );

                    RETURN v_member_id;
                END;
                $$ LANGUAGE plpgsql;
            """))

            # Function to get identity for Discord user
            await session.execute(text("""
                CREATE OR REPLACE FUNCTION identity_for_discord(
                    p_discord_user_id TEXT
                ) RETURNS UUID AS $$
                DECLARE
                    v_member_id UUID;
                BEGIN
                    SELECT member_id INTO v_member_id
                    FROM catalog.member_identities
                    WHERE system = 'discord' AND external_id = p_discord_user_id;

                    RETURN v_member_id;
                END;
                $$ LANGUAGE plpgsql;
            """))

    async def run_full_migration(self) -> None:
        """Run the complete migration process."""
        await self.create_extensions()
        await self.create_schemas()
        await self.db.create_all_tables()
        await self.create_indexes()
        await self.create_functions()

    async def check_migration_status(self) -> dict:
        """Check the current migration status."""
        status = {
            "schemas": {},
            "tables": {},
            "functions": {},
        }

        async with self.db.session_scope() as session:
            # Check schemas
            result = await session.execute(text("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('catalog', 'silver')
            """))
            existing_schemas = [row[0] for row in result.fetchall()]
            status["schemas"]["catalog"] = "catalog" in existing_schemas
            status["schemas"]["silver"] = "silver" in existing_schemas

            # Check tables
            tables_to_check = [
                ("catalog", "members"),
                ("catalog", "member_identities"),
                ("silver", "components"),
                ("silver", "component_members"),
                ("silver", "messages"),
                ("silver", "message_mentions"),
                ("silver", "reactions"),
            ]

            for schema, table in tables_to_check:
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = :schema AND table_name = :table
                """), {"schema": schema, "table": table})
                status["tables"][f"{schema}.{table}"] = result.scalar() > 0

            # Check functions
            result = await session.execute(text("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_name IN ('ensure_member_for_discord', 'identity_for_discord')
            """))
            existing_functions = [row[0] for row in result.fetchall()]
            status["functions"]["ensure_member_for_discord"] = "ensure_member_for_discord" in existing_functions
            status["functions"]["identity_for_discord"] = "identity_for_discord" in existing_functions

        return status