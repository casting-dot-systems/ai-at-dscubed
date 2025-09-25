"""
SQLAlchemy ORM models for brain data processing.
Based on libs/brain and libs/brain_v2 schema definitions.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Boolean, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Member(Base):
    """
    Catalog table for organization members.
    Based on brain_v2/ssot/create_table_members.sql
    """
    __tablename__ = "members"
    __table_args__ = {"schema": "catalog"}

    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(Text)
    preferred_name: Mapped[Optional[str]] = mapped_column(Text)
    primary_email: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[Optional[str]] = mapped_column(Text)
    team: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="active",
        server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default="now()"
    )

    # Relationships
    identities: Mapped[List["MemberIdentity"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        back_populates="author_member", foreign_keys="Message.author_member_id"
    )
    reactions: Mapped[List["Reaction"]] = relationship(back_populates="member")
    component_memberships: Mapped[List["ComponentMember"]] = relationship(
        back_populates="member"
    )

    def __repr__(self) -> str:
        return f"Member(id={self.member_id!r}, name={self.preferred_name or self.full_name!r})"


class MemberIdentity(Base):
    """
    Identity mapping for members across different systems.
    Based on brain_v2/ssot/create_table_member_identities.sql
    """
    __tablename__ = "member_identities"
    __table_args__ = {"schema": "catalog"}

    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("catalog.members.member_id", ondelete="CASCADE"),
        primary_key=True
    )
    system: Mapped[str] = mapped_column(String(50), primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default="now()"
    )

    # Relationships
    member: Mapped["Member"] = relationship(back_populates="identities")

    def __repr__(self) -> str:
        return f"MemberIdentity(system={self.system!r}, external_id={self.external_id!r})"


class Component(Base):
    """
    Components represent channels, threads, and other organizational units.
    Based on brain_v2/silver/create_table_components.sql
    """
    __tablename__ = "components"
    __table_args__ = {"schema": "silver"}

    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    system: Mapped[str] = mapped_column(String(50), primary_key=True)
    component_id: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_component_id: Mapped[Optional[str]] = mapped_column(Text)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at_ts: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    updated_at_ts: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    raw: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    messages: Mapped[List["Message"]] = relationship(back_populates="component")
    members: Mapped[List["ComponentMember"]] = relationship(back_populates="component")

    def __repr__(self) -> str:
        return f"Component(system={self.system!r}, id={self.component_id!r}, name={self.name!r})"


class ComponentMember(Base):
    """
    Association between components and members.
    Based on brain_v2/silver/create_table_component_members.sql
    """
    __tablename__ = "component_members"
    __table_args__ = {"schema": "silver"}

    system: Mapped[str] = mapped_column(String(50), primary_key=True)
    component_id: Mapped[str] = mapped_column(Text, primary_key=True)
    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("catalog.members.member_id"),
        primary_key=True
    )
    role: Mapped[Optional[str]] = mapped_column(String(50))
    joined_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    left_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)

    # Relationships
    component: Mapped["Component"] = relationship(
        back_populates="members",
        foreign_keys=[system, component_id]
    )
    member: Mapped["Member"] = relationship(back_populates="component_memberships")

    def __repr__(self) -> str:
        return f"ComponentMember(component={self.component_id!r}, member_id={self.member_id!r})"


class Message(Base):
    """
    Messages from various communication systems.
    Based on brain_v2/silver/create_table_messages.sql
    """
    __tablename__ = "messages"
    __table_args__ = {"schema": "silver"}

    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    message_id: Mapped[str] = mapped_column(Text, primary_key=True)
    component_id: Mapped[str] = mapped_column(Text, nullable=False)
    author_external_id: Mapped[str] = mapped_column(Text, nullable=False)
    author_member_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("catalog.members.member_id")
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_to_message_id: Mapped[Optional[str]] = mapped_column(Text)
    created_at_ts: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    edited_at_ts: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    deleted_at_ts: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    raw: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    author_member: Mapped[Optional["Member"]] = relationship(
        back_populates="messages", foreign_keys=[author_member_id]
    )
    component: Mapped["Component"] = relationship(
        back_populates="messages",
        foreign_keys=[system, component_id]
    )
    reactions: Mapped[List["Reaction"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    mentions: Mapped[List["MessageMention"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        content_preview = (self.content[:50] + "...") if self.content and len(self.content) > 50 else self.content
        return f"Message(id={self.message_id!r}, content={content_preview!r})"


class MessageMention(Base):
    """
    Mentions within messages.
    Based on brain_v2/silver/create_table_message_mentions.sql
    """
    __tablename__ = "message_mentions"
    __table_args__ = {"schema": "silver"}

    message_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("silver.messages.message_id", ondelete="CASCADE"),
        primary_key=True
    )
    mention_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    mentioned_id: Mapped[str] = mapped_column(Text, primary_key=True)
    member_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("catalog.members.member_id")
    )
    display_text: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    message: Mapped["Message"] = relationship(back_populates="mentions")
    mentioned_member: Mapped[Optional["Member"]] = relationship(
        foreign_keys=[member_id]
    )

    def __repr__(self) -> str:
        return f"MessageMention(type={self.mention_type!r}, id={self.mentioned_id!r})"


class Reaction(Base):
    """
    Message reactions.
    Based on brain_v2/silver/create_table_reactions.sql
    """
    __tablename__ = "reactions"
    __table_args__ = {"schema": "silver"}

    message_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("silver.messages.message_id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    reaction: Mapped[str] = mapped_column(Text, primary_key=True)
    member_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("catalog.members.member_id"),
        primary_key=True,
        index=True
    )
    created_at_ts: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default="now()"
    )

    # Relationships
    message: Mapped["Message"] = relationship(back_populates="reactions")
    member: Mapped[Optional["Member"]] = relationship(back_populates="reactions")

    def __repr__(self) -> str:
        return f"Reaction(message_id={self.message_id!r}, reaction={self.reaction!r})"