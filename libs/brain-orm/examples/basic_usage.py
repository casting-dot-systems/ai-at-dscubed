#!/usr/bin/env python3
"""
Basic usage example for brain-core.

This example demonstrates how to:
1. Set up the database connection
2. Initialize the database schema
3. Use the API to manage data
4. Sync Discord data
5. Export data for analysis
"""

import asyncio
import os
from datetime import datetime, timedelta

from brain_orm import DatabaseManager, BrainCoreAPI, MigrationManager
from brain_orm.extractors import DiscordOrmExtractor


async def main():
    """Main example function."""

    # Setup database connection
    # Make sure to set DATABASE_URL environment variable
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Please set DATABASE_URL environment variable")
        return

    print("Setting up brain-core...")
    db_manager = DatabaseManager(database_url, echo=True)

    # Initialize database if needed
    migration_manager = MigrationManager(db_manager)
    status = await migration_manager.check_migration_status()

    if not all(status["schemas"].values()):
        print("Initializing database...")
        await migration_manager.run_full_migration()

    # Create API instance
    api = BrainCoreAPI(db_manager)

    # Example 1: Create/get a member
    print("\n=== Example 1: Member Management ===")
    member_id = await api.ensure_member_for_discord(
        org_id="example-org",
        discord_user_id="123456789",
        display_name="John Doe",
        email="john@example.com"
    )
    print(f"Created/found member with ID: {member_id}")

    # Get the member back
    member = await api.get_member_by_identity("discord", "123456789", include_identities=True)
    if member:
        print(f"Member: {member.preferred_name} ({member.primary_email})")
        print(f"Identities: {len(member.identities)}")

    # Example 2: Create components and messages
    print("\n=== Example 2: Component and Message Management ===")

    # Create a Discord channel component
    channel = await api.upsert_component(
        org_id="example-org",
        system="discord",
        component_id="987654321",
        component_type="channel",
        name="general",
        raw_data={"description": "General discussion channel"}
    )
    print(f"Created component: {channel.name}")

    # Create a message in the channel
    message = await api.upsert_message(
        org_id="example-org",
        system="discord",
        message_id="msg_123456",
        component_id="987654321",
        author_external_id="123456789",
        content="Hello, world! This is a test message.",
        created_at=datetime.utcnow()
    )
    print(f"Created message: {message.content[:50]}...")

    # Add a reaction to the message
    reaction = await api.add_reaction(
        message_id="msg_123456",
        reaction="👍",
        member_external_id="123456789",
        system="discord"
    )
    print(f"Added reaction: {reaction.reaction}")

    # Example 3: Query data
    print("\n=== Example 3: Querying Data ===")

    # Get messages from the component
    messages = await api.get_messages(
        component_id="987654321",
        system="discord",
        limit=10,
        include_reactions=True,
        include_author=True
    )
    print(f"Found {len(messages)} messages")
    for msg in messages:
        print(f"  - {msg.content[:30]}... by {msg.author_member.preferred_name if msg.author_member else 'Unknown'}")
        if msg.reactions:
            print(f"    Reactions: {[r.reaction for r in msg.reactions]}")

    # Get component statistics
    stats = await api.get_component_stats(system="discord")
    print(f"\nComponent statistics:")
    for stat in stats:
        print(f"  - {stat['name']}: {stat['message_count']} messages")

    # Example 4: Export to DataFrame
    print("\n=== Example 4: Data Export ===")

    # Export messages to pandas DataFrame
    df = await api.export_messages_to_dataframe(
        system="discord",
        start_date=datetime.utcnow() - timedelta(days=30)
    )
    print(f"Exported {len(df)} messages to DataFrame")
    print("DataFrame columns:", list(df.columns))

    # Example 5: Discord sync (if credentials available)
    print("\n=== Example 5: Discord Sync ===")

    bot_token = os.getenv("BOT_KEY")
    guild_id = os.getenv("TEST_SERVER_ID")

    if bot_token and guild_id:
        print("Discord credentials found, performing sync...")
        extractor = DiscordOrmExtractor(api, "example-org", bot_token, int(guild_id))

        # Sync only channels first (faster)
        components = await extractor.sync_discord_channels()
        print(f"Synced {len(components)} Discord components")

        # For a full sync including messages, use:
        # stats = await extractor.full_discord_sync(message_limit_per_channel=100)
        # print(f"Full sync stats: {stats}")
    else:
        print("Discord credentials not available, skipping sync")
        print("Set BOT_KEY and TEST_SERVER_ID environment variables for Discord sync")

    # Cleanup
    await db_manager.close()
    print("\n=== Example completed successfully! ===")


if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    # Run the example
    asyncio.run(main())