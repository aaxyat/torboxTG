#!/usr/bin/env python3
"""
Database module for TorboxTG Bot using Neon.tech PostgreSQL
Handles completed downloads cache and user authentication storage
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Set

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

Base = declarative_base()


class CompletedDownload(Base):
    """Table for storing completed download cache"""

    __tablename__ = "completed_downloads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    normalized_link = Column(String(500), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    download_url = Column(Text, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict:
        """Convert to dictionary format for compatibility"""
        return {
            "filename": self.filename,
            "file_size": self.file_size,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "download_url": self.download_url,
            "completed_at": self.completed_at.isoformat(),
        }


class AuthenticatedUser(Base):
    """Table for storing authenticated users"""

    __tablename__ = "authenticated_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    authenticated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_maker = None

    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine with SSL support for Neon.tech
            connect_args = {}

            # Add SSL configuration for secure connections (Neon.tech requires SSL)
            if "neon.tech" in self.database_url or "ssl" in self.database_url.lower():
                connect_args["ssl"] = "require"

            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args=connect_args,
            )

            # Create session maker
            self.session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        return self.session_maker()

    def get_session_context(self):
        """Get database session as async context manager"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        return self.session_maker()

    # Completed Downloads Operations

    async def get_completed_download(self, normalized_link: str) -> Optional[Dict]:
        """Get completed download by normalized link"""
        try:
            async with self.get_session_context() as session:
                result = await session.execute(
                    select(CompletedDownload).where(
                        CompletedDownload.normalized_link == normalized_link
                    )
                )
                download = result.scalar_one_or_none()
                return download.to_dict() if download else None

        except Exception as e:
            logger.error(f"Error getting completed download: {e}")
            return None

    async def add_completed_download(self, normalized_link: str, file_info: Dict) -> bool:
        """Add or update completed download"""
        try:
            async with self.get_session_context() as session:
                # Use PostgreSQL's ON CONFLICT for upsert
                stmt = insert(CompletedDownload).values(
                    normalized_link=normalized_link,
                    filename=file_info["filename"],
                    file_size=file_info["file_size"],
                    message_id=file_info["message_id"],
                    chat_id=file_info["chat_id"],
                    download_url=file_info["download_url"],
                    completed_at=datetime.utcnow(),
                )

                # Update if exists
                stmt = stmt.on_conflict_do_update(
                    index_elements=[CompletedDownload.normalized_link],
                    set_={
                        "filename": stmt.excluded.filename,
                        "file_size": stmt.excluded.file_size,
                        "message_id": stmt.excluded.message_id,
                        "chat_id": stmt.excluded.chat_id,
                        "download_url": stmt.excluded.download_url,
                        "completed_at": datetime.utcnow(),
                    },
                )

                await session.execute(stmt)
                await session.commit()

                logger.info(f"✅ Saved completed download: {normalized_link}")
                return True

        except Exception as e:
            logger.error(f"❌ Error saving completed download: {e}")
            return False

    async def cleanup_old_downloads(self, keep_count: int = 5000) -> int:
        """Clean up old downloads, keeping the most recent ones"""
        try:
            async with self.get_session_context() as session:
                # Count total downloads
                count_result = await session.execute(
                    select(func.count(CompletedDownload.id))
                )
                total_count = count_result.scalar()

                if total_count <= keep_count:
                    return 0

                # Get IDs of old downloads to delete
                old_downloads = await session.execute(
                    select(CompletedDownload.id)
                    .order_by(CompletedDownload.completed_at.desc())
                    .offset(keep_count)
                )
                old_ids = [row[0] for row in old_downloads.fetchall()]

                if old_ids:
                    # Delete old downloads
                    await session.execute(
                        CompletedDownload.__table__.delete().where(
                            CompletedDownload.id.in_(old_ids)
                        )
                    )
                    await session.commit()

                    deleted_count = len(old_ids)
                    logger.info(f"🧹 Cleaned up {deleted_count} old downloads")
                    return deleted_count

                return 0

        except Exception as e:
            logger.error(f"❌ Error cleaning up old downloads: {e}")
            return 0

    async def get_download_stats(self) -> Dict:
        """Get download statistics"""
        try:
            async with self.get_session_context() as session:
                total_result = await session.execute(
                    select(func.count(CompletedDownload.id))
                )
                total_downloads = total_result.scalar()

                # Get recent downloads (last 24 hours)
                from datetime import datetime, timedelta

                recent_cutoff = datetime.utcnow() - timedelta(days=1)

                recent_result = await session.execute(
                    select(func.count(CompletedDownload.id)).where(
                        CompletedDownload.completed_at >= recent_cutoff
                    )
                )
                recent_downloads = recent_result.scalar()

                return {
                    "total_downloads": total_downloads,
                    "recent_downloads": recent_downloads,
                    "cache_hit_rate": "N/A",  # Can be calculated over time
                }

        except Exception as e:
            logger.error(f"Error getting download stats: {e}")
            return {"total_downloads": 0, "recent_downloads": 0, "cache_hit_rate": "N/A"}

    # Authenticated Users Operations

    async def get_authenticated_users(self) -> Set[int]:
        """Get all authenticated user IDs"""
        try:
            async with self.get_session_context() as session:
                result = await session.execute(select(AuthenticatedUser.user_id))
                user_ids = {row[0] for row in result.fetchall()}
                return user_ids

        except Exception as e:
            logger.error(f"Error getting authenticated users: {e}")
            return set()

    async def add_authenticated_user(self, user_id: int) -> bool:
        """Add authenticated user"""
        try:
            async with self.get_session_context() as session:
                # Use upsert to avoid duplicates
                stmt = insert(AuthenticatedUser).values(
                    user_id=user_id, authenticated_at=datetime.utcnow()
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=[AuthenticatedUser.user_id],
                    set_={"authenticated_at": datetime.utcnow()},
                )

                await session.execute(stmt)
                await session.commit()

                logger.info(f"✅ Added authenticated user: {user_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Error adding authenticated user: {e}")
            return False

    async def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        try:
            async with self.get_session_context() as session:
                result = await session.execute(
                    select(AuthenticatedUser).where(AuthenticatedUser.user_id == user_id)
                )
                return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.error(f"Error checking user authentication: {e}")
            return False


# Global database instance
db_manager: Optional[DatabaseManager] = None


async def init_database(database_url: str) -> DatabaseManager:
    """Initialize global database manager"""
    global db_manager

    # Parse and fix the database URL for asyncpg compatibility
    if database_url.startswith("postgresql://"):
        # Convert to asyncpg format and handle SSL parameters
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Handle SSL parameters that asyncpg doesn't recognize in URL format
        if "sslmode=" in database_url:
            # Remove sslmode from URL as asyncpg handles SSL differently
            import re

            database_url = re.sub(r"[?&]sslmode=[^&]*", "", database_url)
            database_url = re.sub(r"\?&", "?", database_url)  # Fix malformed query string
            database_url = database_url.rstrip("?&")  # Remove trailing ? or &
    elif not database_url.startswith("postgresql+asyncpg://"):
        raise ValueError("Invalid database URL format. Must start with postgresql://")

    db_manager = DatabaseManager(database_url)
    await db_manager.initialize()
    return db_manager


async def get_db() -> DatabaseManager:
    """Get global database manager"""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    return db_manager


async def close_database():
    """Close global database manager"""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None
