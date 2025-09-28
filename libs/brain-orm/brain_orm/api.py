"""
High-level API for brain-core data operations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

import pandas as pd
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .database import DatabaseManager
from .models import (
    Member,
    MemberIdentity,
    Component,
    ComponentMember,
    Message,
    MessageMention,
    Reaction,
)


class BrainCoreAPI:
    """High-level API for brain-core data operations."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize API with database manager.

        Args:
            db_manager: DatabaseManager instance for database operations.
        """
        self.db = db_manager

    async def ensure_member_for_discord(
        self,
        org_id: str,
        discord_user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> UUID:
        """
        Ensure a member exists for a Discord user, creating if necessary.
        Based on brain_v2 ensure_member_for_discord function.

        Args:
            org_id: Organization identifier
            discord_user_id: Discord user ID
            display_name: User's display name
            email: User's email address

        Returns:
            UUID of the member
        """
        async with self.db.session_scope() as session:
            # Check if identity already exists
            stmt = (
                select(MemberIdentity)
                .where(
                    and_(
                        MemberIdentity.system == "discord",
                        MemberIdentity.external_id == discord_user_id,
                    )
                )
                .options(selectinload(MemberIdentity.member))
            )
            result = await session.execute(stmt)
            identity = result.scalar_one_or_none()

            if identity:
                # Update existing identity if needed
                if display_name and identity.display_name != display_name:
                    identity.display_name = display_name
                if email and identity.email != email:
                    identity.email = email
                identity.updated_at = datetime.utcnow()
                return identity.member_id

            # Create new member and identity
            member = Member(
                org_id=org_id,
                preferred_name=display_name,
                primary_email=email,
            )
            session.add(member)
            await session.flush()  # Get the member_id

            identity = MemberIdentity(
                member_id=member.member_id,
                system="discord",
                external_id=discord_user_id,
                display_name=display_name,
                email=email,
            )
            session.add(identity)

            return member.member_id

    async def get_member_by_identity(
        self,
        system: str,
        external_id: str,
        include_identities: bool = False,
    ) -> Optional[Member]:
        """
        Get a member by their external identity.

        Args:
            system: System name (e.g., 'discord', 'notion')
            external_id: External ID in the system
            include_identities: Whether to include all identities

        Returns:
            Member object or None if not found
        """
        async with self.db.session_scope() as session:
            stmt = (
                select(Member)
                .join(MemberIdentity)
                .where(
                    and_(
                        MemberIdentity.system == system,
                        MemberIdentity.external_id == external_id,
                    )
                )
            )

            if include_identities:
                stmt = stmt.options(selectinload(Member.identities))

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upsert_component(
        self,
        org_id: str,
        system: str,
        component_id: str,
        component_type: str,
        name: Optional[str] = None,
        parent_component_id: Optional[str] = None,
        is_active: bool = True,
        raw_data: Optional[dict] = None,
    ) -> Component:
        """
        Create or update a component.

        Args:
            org_id: Organization identifier
            system: System name (e.g., 'discord')
            component_id: Component ID in the system
            component_type: Type of component (e.g., 'channel', 'thread')
            name: Component name
            parent_component_id: Parent component ID
            is_active: Whether component is active
            raw_data: Raw component data

        Returns:
            Component object
        """
        async with self.db.session_scope() as session:
            # Try to get existing component
            stmt = select(Component).where(
                and_(
                    Component.system == system,
                    Component.component_id == component_id,
                )
            )
            result = await session.execute(stmt)
            component = result.scalar_one_or_none()

            if component:
                # Update existing
                component.org_id = org_id
                component.component_type = component_type
                component.name = name
                component.parent_component_id = parent_component_id
                component.is_active = is_active
                component.updated_at_ts = datetime.utcnow()
                if raw_data:
                    component.raw = raw_data
            else:
                # Create new
                component = Component(
                    org_id=org_id,
                    system=system,
                    component_id=component_id,
                    parent_component_id=parent_component_id,
                    component_type=component_type,
                    name=name,
                    is_active=is_active,
                    created_at_ts=datetime.utcnow(),
                    updated_at_ts=datetime.utcnow(),
                    raw=raw_data,
                )
                session.add(component)

            return component

    async def upsert_message(
        self,
        org_id: str,
        system: str,
        message_id: str,
        component_id: str,
        author_external_id: str,
        content: Optional[str] = None,
        has_attachments: bool = False,
        reply_to_message_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        edited_at: Optional[datetime] = None,
        raw_data: Optional[dict] = None,
    ) -> Message:
        """
        Create or update a message.

        Args:
            org_id: Organization identifier
            system: System name (e.g., 'discord')
            message_id: Message ID in the system
            component_id: Component (channel/thread) ID
            author_external_id: Author's external ID
            content: Message content
            has_attachments: Whether message has attachments
            reply_to_message_id: ID of message being replied to
            created_at: Message creation timestamp
            edited_at: Message edit timestamp
            raw_data: Raw message data

        Returns:
            Message object
        """
        async with self.db.session_scope() as session:
            # Try to get existing message
            stmt = select(Message).where(Message.message_id == message_id)
            result = await session.execute(stmt)
            message = result.scalar_one_or_none()

            # Get author member ID if exists
            author_member_id = None
            if author_external_id:
                identity_stmt = select(MemberIdentity.member_id).where(
                    and_(
                        MemberIdentity.system == system,
                        MemberIdentity.external_id == author_external_id,
                    )
                )
                identity_result = await session.execute(identity_stmt)
                author_member_id = identity_result.scalar_one_or_none()

            if message:
                # Update existing
                message.org_id = org_id
                message.system = system
                message.component_id = component_id
                message.author_external_id = author_external_id
                message.author_member_id = author_member_id
                message.content = content
                message.has_attachments = has_attachments
                message.reply_to_message_id = reply_to_message_id
                message.edited_at_ts = edited_at or datetime.utcnow()
                if raw_data:
                    message.raw = raw_data
            else:
                # Create new
                message = Message(
                    org_id=org_id,
                    system=system,
                    message_id=message_id,
                    component_id=component_id,
                    author_external_id=author_external_id,
                    author_member_id=author_member_id,
                    content=content,
                    has_attachments=has_attachments,
                    reply_to_message_id=reply_to_message_id,
                    created_at_ts=created_at or datetime.utcnow(),
                    edited_at_ts=edited_at,
                    raw=raw_data,
                )
                session.add(message)

            return message

    async def add_reaction(
        self,
        message_id: str,
        reaction: str,
        member_external_id: str,
        system: str = "discord",
        created_at: Optional[datetime] = None,
    ) -> Reaction:
        """
        Add a reaction to a message.

        Args:
            message_id: ID of the message
            reaction: Reaction emoji/text
            member_external_id: External ID of the member reacting
            system: System name (default: 'discord')
            created_at: When the reaction was created

        Returns:
            Reaction object
        """
        async with self.db.session_scope() as session:
            # Get member ID
            member_id = None
            if member_external_id:
                identity_stmt = select(MemberIdentity.member_id).where(
                    and_(
                        MemberIdentity.system == system,
                        MemberIdentity.external_id == member_external_id,
                    )
                )
                identity_result = await session.execute(identity_stmt)
                member_id = identity_result.scalar_one_or_none()

            # Check if reaction already exists
            stmt = select(Reaction).where(
                and_(
                    Reaction.message_id == message_id,
                    Reaction.reaction == reaction,
                    Reaction.member_id == member_id,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return existing

            # Create new reaction
            reaction_obj = Reaction(
                message_id=message_id,
                reaction=reaction,
                member_id=member_id,
                created_at_ts=created_at or datetime.utcnow(),
            )
            session.add(reaction_obj)
            return reaction_obj

    async def get_messages(
        self,
        component_id: Optional[str] = None,
        author_member_id: Optional[UUID] = None,
        system: Optional[str] = None,
        limit: Optional[int] = None,
        include_reactions: bool = False,
        include_author: bool = False,
    ) -> List[Message]:
        """
        Get messages with optional filtering.

        Args:
            component_id: Filter by component ID
            author_member_id: Filter by author member ID
            system: Filter by system
            limit: Maximum number of messages to return
            include_reactions: Whether to include reactions
            include_author: Whether to include author member

        Returns:
            List of Message objects
        """
        async with self.db.session_scope() as session:
            stmt = select(Message).order_by(Message.created_at_ts.desc())

            # Apply filters
            if component_id:
                stmt = stmt.where(Message.component_id == component_id)
            if author_member_id:
                stmt = stmt.where(Message.author_member_id == author_member_id)
            if system:
                stmt = stmt.where(Message.system == system)
            if limit:
                stmt = stmt.limit(limit)

            # Apply eager loading
            if include_reactions:
                stmt = stmt.options(selectinload(Message.reactions))
            if include_author:
                stmt = stmt.options(selectinload(Message.author_member))

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_component_stats(
        self, system: Optional[str] = None, component_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get statistics about components.

        Args:
            system: Filter by system
            component_type: Filter by component type

        Returns:
            List of component statistics
        """
        async with self.db.session_scope() as session:
            stmt = (
                select(
                    Component.system,
                    Component.component_type,
                    Component.name,
                    Component.component_id,
                    func.count(Message.message_id).label("message_count"),
                    func.max(Message.created_at_ts).label("last_message_at"),
                )
                .outerjoin(
                    Message,
                    and_(
                        Message.component_id == Component.component_id,
                        Message.system == Component.system,
                    ),
                )
                .group_by(
                    Component.system,
                    Component.component_type,
                    Component.name,
                    Component.component_id,
                )
            )

            if system:
                stmt = stmt.where(Component.system == system)
            if component_type:
                stmt = stmt.where(Component.component_type == component_type)

            result = await session.execute(stmt)
            return [row._asdict() for row in result.all()]

    async def export_messages_to_dataframe(
        self,
        component_id: Optional[str] = None,
        system: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Export messages to a pandas DataFrame for analysis.

        Args:
            component_id: Filter by component ID
            system: Filter by system
            start_date: Filter messages after this date
            end_date: Filter messages before this date

        Returns:
            pandas DataFrame with message data
        """
        async with self.db.session_scope() as session:
            stmt = (
                select(
                    Message.message_id,
                    Message.org_id,
                    Message.system,
                    Message.component_id,
                    Message.author_external_id,
                    Message.author_member_id,
                    Message.content,
                    Message.has_attachments,
                    Message.reply_to_message_id,
                    Message.created_at_ts,
                    Message.edited_at_ts,
                    Message.deleted_at_ts,
                    Component.name.label("component_name"),
                    Component.component_type,
                    Member.preferred_name.label("author_name"),
                )
                .outerjoin(
                    Component,
                    and_(
                        Component.component_id == Message.component_id,
                        Component.system == Message.system,
                    ),
                )
                .outerjoin(Member, Member.member_id == Message.author_member_id)
                .order_by(Message.created_at_ts.desc())
            )

            # Apply filters
            if component_id:
                stmt = stmt.where(Message.component_id == component_id)
            if system:
                stmt = stmt.where(Message.system == system)
            if start_date:
                stmt = stmt.where(Message.created_at_ts >= start_date)
            if end_date:
                stmt = stmt.where(Message.created_at_ts <= end_date)

            result = await session.execute(stmt)
            data = [row._asdict() for row in result.all()]

            return pd.DataFrame(data)