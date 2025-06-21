#!/usr/bin/env python3
"""
Startup script for TorboxTG Bot with enhanced error handling and environment validation
"""

import os
import sys
from pathlib import Path


def check_requirements():
    """Check if all required packages are installed"""
    try:
        import aiofiles
        import aiohttp
        import asyncpg
        import sqlalchemy
        import telegram
        from asyncio_throttle import Throttler
        from dotenv import load_dotenv

        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nPlease install dependencies:")
        print("pip install -r requirements.txt")
        print("or")
        print("pip install -e .")
        return False


def check_environment():
    """Check if environment variables are properly configured"""
    from dotenv import load_dotenv

    # Load environment variables
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv()
        print("✅ Found .env file")
    else:
        print("⚠️  No .env file found")
        print("   Copy config.env.template to .env and configure your tokens")

    # Check required variables
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    torbox_token = os.getenv("TORBOX_API_TOKEN")
    auth_key = os.getenv("AUTH_KEY")
    database_url = os.getenv("DATABASE_URL")

    if not telegram_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        print("   Get your token from @BotFather on Telegram")
        return False

    if not torbox_token:
        print("❌ TORBOX_API_TOKEN not found")
        print("   Get your token from https://torbox.app")
        return False

    if not auth_key:
        print("❌ AUTH_KEY not found")
        print("   Set a secure authentication key in your .env file")
        return False

    if not database_url:
        print("❌ DATABASE_URL not found")
        print("   Set your Neon.tech PostgreSQL connection string")
        print("   Format: postgresql://username:password@hostname/database?sslmode=require")
        return False

    # Validate token format
    if not telegram_token.count(":") == 1:
        print("❌ TELEGRAM_BOT_TOKEN appears to be invalid")
        print("   Should be in format: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        return False

    # Validate database URL format
    if not database_url.startswith("postgresql://"):
        print("❌ DATABASE_URL appears to be invalid")
        print("   Should start with: postgresql://")
        return False

    print("✅ Environment variables configured")
    return True


async def check_database_connection():
    """Test database connection"""
    import asyncio

    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found")
        return False

    try:
        print("🔄 Testing database connection...")

        # Import database module
        from database import close_database, get_db, init_database

        # Test connection
        await init_database(database_url)
        db = await get_db()

        # Test basic operations
        stats = await db.get_download_stats()
        users = await db.get_authenticated_users()

        print(f"✅ Database connection successful!")
        print(f"   📊 Downloads in database: {stats['total_downloads']}")
        print(f"   👥 Authenticated users: {len(users)}")

        await close_database()
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check your DATABASE_URL is correct")
        print("2. Ensure your Neon.tech database is running")
        print("3. Verify network connectivity")
        print("4. Run: python setup_db.py setup")
        return False


async def main():
    """Main startup function"""
    print("🤖 TorboxTG Bot Startup")
    print("=" * 40)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check environment
    if not check_environment():
        print("\n💡 Setup Instructions:")
        print("1. Copy config.env.template to .env")
        print("2. Edit .env with your tokens:")
        print("   - TELEGRAM_BOT_TOKEN from @BotFather")
        print("   - TORBOX_API_TOKEN from torbox.app")
        print("   - AUTH_KEY for bot authentication")
        print("   - DATABASE_URL from Neon.tech")
        print("3. Run: python setup_db.py setup")
        print("4. Run this script again")
        sys.exit(1)

    # Check database connection
    if not await check_database_connection():
        print("\n💡 Database Setup Instructions:")
        print("1. Ensure your DATABASE_URL is correct")
        print("2. Run: python setup_db.py setup")
        print("3. Check your Neon.tech database is running")
        sys.exit(1)

    print("\n🚀 Starting bot...")
    print("=" * 40)

    # Import and run the main bot
    try:
        from main import main as bot_main

        await bot_main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        print("\nCheck the logs (torboxtg.log) for more details")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
