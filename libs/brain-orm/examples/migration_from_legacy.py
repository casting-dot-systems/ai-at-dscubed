#!/usr/bin/env python3
"""
Migration example for transitioning from legacy brain/brain_v2 to brain-core.

This example shows how to:
1. Load data from existing CSV/DataFrame formats
2. Migrate to the new SQLAlchemy ORM structure
3. Validate the migration
"""

import asyncio
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from brain_orm import DatabaseManager, BrainCoreAPI, MigrationManager
from brain_orm.extractors import DataFrameLoader


class LegacyMigrator:
    """Handles migration from legacy brain data formats to brain-core."""

    def __init__(self, api: BrainCoreAPI):
        self.api = api

    async def migrate_legacy_discord_data(
        self,
        csv_path: str,
        org_id: str,
        system: str = "discord"
    ) -> Dict[str, int]:
        """
        Migrate legacy Discord CSV data to brain-core.

        Expected CSV format (from original brain/bronze output):
        - channel_id, channel_name, thread_name, thread_id, message_id
        - discord_username, discord_user_id, content
        - chat_created_at, chat_edited_at, is_thread
        """
        print(f"Loading legacy data from {csv_path}...")

        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} records from CSV")

        # Track statistics
        stats = {
            "components_created": 0,
            "members_created": 0,
            "messages_created": 0,
            "errors": 0
        }

        # Process unique components (channels and threads)
        print("Processing components...")
        unique_channels = df[['channel_id', 'channel_name']].drop_duplicates()

        for _, row in unique_channels.iterrows():
            try:
                await self.api.upsert_component(
                    org_id=org_id,
                    system=system,
                    component_id=str(row['channel_id']),
                    component_type="channel",
                    name=row['channel_name'],
                    raw_data={"migrated_from": "legacy_csv"}
                )
                stats["components_created"] += 1
            except Exception as e:
                print(f"Error creating channel {row['channel_id']}: {e}")
                stats["errors"] += 1

        # Process threads
        thread_df = df[df['is_thread'] == True][['thread_id', 'thread_name', 'channel_id']].drop_duplicates()
        for _, row in thread_df.iterrows():
            try:
                await self.api.upsert_component(
                    org_id=org_id,
                    system=system,
                    component_id=str(row['thread_id']),
                    component_type="thread",
                    name=row['thread_name'],
                    parent_component_id=str(row['channel_id']),
                    raw_data={"migrated_from": "legacy_csv"}
                )
                stats["components_created"] += 1
            except Exception as e:
                print(f"Error creating thread {row['thread_id']}: {e}")
                stats["errors"] += 1

        # Process members
        print("Processing members...")
        unique_members = df[['discord_user_id', 'discord_username']].drop_duplicates()

        for _, row in unique_members.iterrows():
            try:
                await self.api.ensure_member_for_discord(
                    org_id=org_id,
                    discord_user_id=str(row['discord_user_id']),
                    display_name=row['discord_username']
                )
                stats["members_created"] += 1
            except Exception as e:
                print(f"Error creating member {row['discord_user_id']}: {e}")
                stats["errors"] += 1

        # Process messages
        print("Processing messages...")
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")

            for _, row in batch.iterrows():
                try:
                    # Determine component_id (use thread_id if it's a thread message, otherwise channel_id)
                    component_id = str(row['thread_id']) if row['is_thread'] and pd.notna(row['thread_id']) else str(row['channel_id'])

                    # Parse timestamps
                    created_at = pd.to_datetime(row['chat_created_at']) if pd.notna(row['chat_created_at']) else None
                    edited_at = pd.to_datetime(row['chat_edited_at']) if pd.notna(row['chat_edited_at']) else None

                    await self.api.upsert_message(
                        org_id=org_id,
                        system=system,
                        message_id=str(row['message_id']),
                        component_id=component_id,
                        author_external_id=str(row['discord_user_id']),
                        content=row['content'] if pd.notna(row['content']) else None,
                        created_at=created_at,
                        edited_at=edited_at,
                        raw_data={
                            "migrated_from": "legacy_csv",
                            "original_channel_name": row['channel_name'],
                            "original_thread_name": row['thread_name'] if pd.notna(row['thread_name']) else None,
                            "is_thread": bool(row['is_thread'])
                        }
                    )
                    stats["messages_created"] += 1

                except Exception as e:
                    print(f"Error creating message {row['message_id']}: {e}")
                    stats["errors"] += 1

        return stats

    async def validate_migration(self, org_id: str) -> Dict[str, Any]:
        """Validate the migration by checking data integrity."""
        print("Validating migration...")

        validation_results = {
            "members_count": 0,
            "components_count": 0,
            "messages_count": 0,
            "orphaned_messages": 0,
            "members_with_identities": 0
        }

        # Check member statistics
        async with self.api.db.session_scope() as session:
            from brain_orm.models import Member, Component, Message, MemberIdentity
            from sqlalchemy import select, func

            # Count members
            result = await session.execute(select(func.count(Member.member_id)))
            validation_results["members_count"] = result.scalar()

            # Count components
            result = await session.execute(select(func.count()).select_from(Component))
            validation_results["components_count"] = result.scalar()

            # Count messages
            result = await session.execute(select(func.count(Message.message_id)))
            validation_results["messages_count"] = result.scalar()

            # Check for orphaned messages (messages without valid components)
            result = await session.execute(
                select(func.count(Message.message_id))
                .outerjoin(Component, Message.component_id == Component.component_id)
                .where(Component.component_id.is_(None))
            )
            validation_results["orphaned_messages"] = result.scalar()

            # Check members with Discord identities
            result = await session.execute(
                select(func.count(Member.member_id.distinct()))
                .join(MemberIdentity)
                .where(MemberIdentity.system == "discord")
            )
            validation_results["members_with_identities"] = result.scalar()

        print("Validation Results:")
        print(f"  Members: {validation_results['members_count']}")
        print(f"  Components: {validation_results['components_count']}")
        print(f"  Messages: {validation_results['messages_count']}")
        print(f"  Orphaned Messages: {validation_results['orphaned_messages']}")
        print(f"  Members with Discord Identities: {validation_results['members_with_identities']}")

        return validation_results


async def main():
    """Main migration example."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Setup
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Please set DATABASE_URL environment variable")
        return

    db_manager = DatabaseManager(database_url, echo=False)

    # Initialize database
    migration_manager = MigrationManager(db_manager)
    print("Checking database status...")
    status = await migration_manager.check_migration_status()

    if not all(status["schemas"].values()):
        print("Initializing database...")
        await migration_manager.run_full_migration()

    # Create API and migrator
    api = BrainCoreAPI(db_manager)
    migrator = LegacyMigrator(api)

    # Example migration paths - update these to your actual data locations
    legacy_csv_path = "path/to/your/legacy_discord_data.csv"

    # Check if example data exists
    if Path(legacy_csv_path).exists():
        print(f"Found legacy data at {legacy_csv_path}")

        # Perform migration
        migration_stats = await migrator.migrate_legacy_discord_data(
            csv_path=legacy_csv_path,
            org_id="migrated-org"
        )

        print(f"\nMigration completed!")
        print(f"Statistics: {migration_stats}")

        # Validate migration
        validation_results = await migrator.validate_migration("migrated-org")

        # Check for issues
        if validation_results["orphaned_messages"] > 0:
            print(f"WARNING: {validation_results['orphaned_messages']} orphaned messages found!")

        print("\nMigration validation completed!")

    else:
        print(f"Legacy data not found at {legacy_csv_path}")
        print("This is expected if you don't have legacy data to migrate.")

        # Create some sample data to demonstrate the structure
        print("Creating sample data instead...")

        # Sample member
        member_id = await api.ensure_member_for_discord(
            org_id="sample-org",
            discord_user_id="sample_user_123",
            display_name="Sample User"
        )

        # Sample component
        component = await api.upsert_component(
            org_id="sample-org",
            system="discord",
            component_id="sample_channel_456",
            component_type="channel",
            name="sample-channel"
        )

        # Sample message
        message = await api.upsert_message(
            org_id="sample-org",
            system="discord",
            message_id="sample_msg_789",
            component_id="sample_channel_456",
            author_external_id="sample_user_123",
            content="This is a sample migrated message"
        )

        print("Sample data created successfully!")

        # Show component stats
        stats = await api.get_component_stats()
        print(f"Component stats: {len(stats)} components found")

    await db_manager.close()
    print("Migration example completed!")


if __name__ == "__main__":
    asyncio.run(main())