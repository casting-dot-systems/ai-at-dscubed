#!/usr/bin/env python3
"""
Brain Core CLI - Command line interface for brain-core operations.
"""

import asyncio
import os
from typing import Optional
import click
from dotenv import load_dotenv

from ..database import DatabaseManager
from ..migrations import MigrationManager
from ..api import BrainCoreAPI
from ..extractors import DiscordOrmExtractor


@click.group()
@click.option('--database-url', envvar='DATABASE_URL', help='Database URL')
@click.option('--echo/--no-echo', default=False, help='Echo SQL statements')
@click.pass_context
def cli(ctx, database_url: Optional[str], echo: bool):
    """Brain Core CLI - Manage brain data processing operations."""
    if not database_url:
        click.echo("Error: DATABASE_URL must be provided or set as environment variable", err=True)
        ctx.exit(1)

    ctx.ensure_object(dict)
    ctx.obj['database_url'] = database_url
    ctx.obj['echo'] = echo


@cli.group()
@click.pass_context
def db(ctx):
    """Database management commands."""
    pass


@db.command()
@click.pass_context
def init(ctx):
    """Initialize database with schemas, tables, and functions."""
    async def _init():
        db_manager = DatabaseManager(ctx.obj['database_url'], echo=ctx.obj['echo'])
        migration_manager = MigrationManager(db_manager)

        click.echo("Initializing database...")
        await migration_manager.run_full_migration()
        click.echo("Database initialization completed!")

        await db_manager.close()

    asyncio.run(_init())


@db.command()
@click.pass_context
def status(ctx):
    """Check database migration status."""
    async def _status():
        db_manager = DatabaseManager(ctx.obj['database_url'], echo=ctx.obj['echo'])
        migration_manager = MigrationManager(db_manager)

        status = await migration_manager.check_migration_status()

        click.echo("Database Migration Status:")
        click.echo("=" * 30)

        click.echo("\nSchemas:")
        for schema, exists in status["schemas"].items():
            status_icon = "✓" if exists else "✗"
            click.echo(f"  {status_icon} {schema}")

        click.echo("\nTables:")
        for table, exists in status["tables"].items():
            status_icon = "✓" if exists else "✗"
            click.echo(f"  {status_icon} {table}")

        click.echo("\nFunctions:")
        for func, exists in status["functions"].items():
            status_icon = "✓" if exists else "✗"
            click.echo(f"  {status_icon} {func}")

        await db_manager.close()

    asyncio.run(_status())


@cli.group()
@click.pass_context
def sync(ctx):
    """Data synchronization commands."""
    pass


@sync.command()
@click.option('--org-id', required=True, help='Organization ID')
@click.option('--bot-token', envvar='BOT_KEY', help='Discord bot token')
@click.option('--guild-id', envvar='TEST_SERVER_ID', type=int, help='Discord guild ID')
@click.option('--message-limit', type=int, help='Limit messages per channel')
@click.option('--channels-only', is_flag=True, help='Sync only channels, not messages')
@click.pass_context
def discord(ctx, org_id: str, bot_token: Optional[str], guild_id: Optional[int],
           message_limit: Optional[int], channels_only: bool):
    """Sync Discord data to database."""
    async def _sync_discord():
        db_manager = DatabaseManager(ctx.obj['database_url'], echo=ctx.obj['echo'])
        api = BrainCoreAPI(db_manager)
        extractor = DiscordOrmExtractor(api, org_id, bot_token, guild_id)

        if channels_only:
            click.echo("Syncing Discord channels...")
            components = await extractor.sync_discord_channels()
            click.echo(f"Synced {len(components)} components")
        else:
            click.echo("Performing full Discord sync...")
            stats = await extractor.full_discord_sync(message_limit)
            click.echo(f"Sync completed: {stats}")

        await db_manager.close()

    asyncio.run(_sync_discord())


@cli.group()
@click.pass_context
def export(ctx):
    """Data export commands."""
    pass


@export.command()
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--component-id', help='Filter by component ID')
@click.option('--system', help='Filter by system')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.pass_context
def messages(ctx, output: str, component_id: Optional[str], system: Optional[str],
            start_date: Optional[str], end_date: Optional[str]):
    """Export messages to CSV file."""
    async def _export_messages():
        from datetime import datetime
        import pandas as pd

        db_manager = DatabaseManager(ctx.obj['database_url'], echo=ctx.obj['echo'])
        api = BrainCoreAPI(db_manager)

        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        click.echo("Exporting messages...")
        df = await api.export_messages_to_dataframe(
            component_id=component_id,
            system=system,
            start_date=start_dt,
            end_date=end_dt
        )

        df.to_csv(output, index=False)
        click.echo(f"Exported {len(df)} messages to {output}")

        await db_manager.close()

    asyncio.run(_export_messages())


@cli.command()
@click.option('--system', help='Filter by system')
@click.option('--component-type', help='Filter by component type')
@click.pass_context
def stats(ctx, system: Optional[str], component_type: Optional[str]):
    """Show component statistics."""
    async def _stats():
        db_manager = DatabaseManager(ctx.obj['database_url'], echo=ctx.obj['echo'])
        api = BrainCoreAPI(db_manager)

        stats = await api.get_component_stats(system, component_type)

        click.echo("Component Statistics:")
        click.echo("=" * 50)

        for stat in stats:
            click.echo(f"System: {stat['system']}")
            click.echo(f"Type: {stat['component_type']}")
            click.echo(f"Name: {stat['name']}")
            click.echo(f"Component ID: {stat['component_id']}")
            click.echo(f"Message Count: {stat['message_count']}")
            click.echo(f"Last Message: {stat['last_message_at']}")
            click.echo("-" * 30)

        await db_manager.close()

    asyncio.run(_stats())


if __name__ == '__main__':
    load_dotenv()
    cli()