"""
Database management utilities for brain-core.
"""

import os
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from .models import Base


class DatabaseManager:
    """Manages database connections and sessions for brain-core."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        async_database_url: Optional[str] = None,
        echo: bool = False
    ):
        """
        Initialize database manager.

        Args:
            database_url: Synchronous database URL. If None, uses DATABASE_URL env var.
            async_database_url: Async database URL. If None, uses ASYNC_DATABASE_URL env var
                               or converts database_url to async.
            echo: Whether to echo SQL statements.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.echo = echo

        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided or set as environment variable")

        # Setup async URL
        if async_database_url:
            self.async_database_url = async_database_url
        elif os.getenv("ASYNC_DATABASE_URL"):
            self.async_database_url = os.getenv("ASYNC_DATABASE_URL")
        else:
            # Convert sync URL to async (postgresql -> postgresql+asyncpg)
            if self.database_url.startswith("postgresql://"):
                self.async_database_url = self.database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )
            else:
                raise ValueError("Cannot automatically convert database URL to async format")

        # Create engines
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get or create synchronous database engine."""
        if self._engine is None:
            self._engine = create_engine(self.database_url, echo=self.echo)
        return self._engine

    @property
    def async_engine(self) -> AsyncEngine:
        """Get or create asynchronous database engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(self.async_database_url, echo=self.echo)
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create synchronous session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker:
        """Get or create asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine, expire_on_commit=False
            )
        return self._async_session_factory

    def create_session(self) -> Session:
        """Create a new synchronous database session."""
        return self.session_factory()

    def create_async_session(self) -> AsyncSession:
        """Create a new asynchronous database session."""
        return self.async_session_factory()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope around a series of operations.

        Usage:
            async with db_manager.session_scope() as session:
                # perform database operations
                pass
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_all_tables(self) -> None:
        """Create all tables defined in the models."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all_tables(self) -> None:
        """Drop all tables defined in the models."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def create_all_tables_sync(self) -> None:
        """Create all tables defined in the models (synchronous)."""
        Base.metadata.create_all(self.engine)

    def drop_all_tables_sync(self) -> None:
        """Drop all tables defined in the models (synchronous)."""
        Base.metadata.drop_all(self.engine)

    async def close(self) -> None:
        """Close all database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._engine:
            self._engine.dispose()