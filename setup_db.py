#!/usr/bin/env python3
"""
Database setup script for TorboxTG Bot
Helps initialize and manage the Neon.tech PostgreSQL database
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Import database module
from database import close_database, get_db, init_database

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def setup_database():
    """Initialize database and create tables"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables")
        print("Please set your Neon.tech PostgreSQL connection string in .env file")
        return False

    try:
        print("🔄 Initializing database...")
        await init_database(DATABASE_URL)
        print("✅ Database initialized successfully!")

        # Test the connection
        db = await get_db()
        stats = await db.get_download_stats()
        print(f"📊 Database ready - Total downloads: {stats['total_downloads']}")

        return True

    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    finally:
        await close_database()


async def cleanup_database():
    """Clean up old downloads from database"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    try:
        print("🔄 Connecting to database...")
        await init_database(DATABASE_URL)

        db = await get_db()

        # Get current stats
        stats = await db.get_download_stats()
        print(f"📊 Current downloads in database: {stats['total_downloads']}")

        # Clean up old downloads (keep 1000 most recent)
        deleted_count = await db.cleanup_old_downloads(keep_count=1000)

        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} old downloads")
        else:
            print("✅ No cleanup needed")

        # Get updated stats
        stats = await db.get_download_stats()
        print(f"📊 Downloads after cleanup: {stats['total_downloads']}")

        return True

    except Exception as e:
        print(f"❌ Failed to cleanup database: {e}")
        return False
    finally:
        await close_database()


async def show_stats():
    """Show database statistics"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables")
        return False

    try:
        print("🔄 Connecting to database...")
        await init_database(DATABASE_URL)

        db = await get_db()

        # Get download stats
        stats = await db.get_download_stats()
        print("\n📊 Database Statistics:")
        print(f"   Total downloads: {stats['total_downloads']}")
        print(f"   Recent downloads (24h): {stats['recent_downloads']}")

        # Get user stats
        users = await db.get_authenticated_users()
        print(f"   Authenticated users: {len(users)}")

        return True

    except Exception as e:
        print(f"❌ Failed to get database stats: {e}")
        return False
    finally:
        await close_database()


def print_help():
    """Print help information"""
    print(
        """
🤖 TorboxTG Database Setup Script

Commands:
  setup     - Initialize database and create tables
  cleanup   - Clean up old downloads (keep 1000 most recent)
  stats     - Show database statistics
  help      - Show this help message

Usage:
  python setup_db.py <command>

Examples:
  python setup_db.py setup
  python setup_db.py cleanup
  python setup_db.py stats

Make sure to set DATABASE_URL in your .env file first!
    """
    )


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    if command == "setup":
        success = await setup_database()
        if success:
            print("\n🎉 Database setup complete! You can now run the bot.")
        else:
            print("\n❌ Database setup failed. Please check your DATABASE_URL.")
            sys.exit(1)

    elif command == "cleanup":
        success = await cleanup_database()
        if not success:
            sys.exit(1)

    elif command == "stats":
        success = await show_stats()
        if not success:
            sys.exit(1)

    elif command == "help":
        print_help()

    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
