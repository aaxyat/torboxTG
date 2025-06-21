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

    if not telegram_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        print("   Get your token from @BotFather on Telegram")
        return False

    if not torbox_token:
        print("❌ TORBOX_API_TOKEN not found")
        print("   Get your token from https://torbox.app")
        return False

    # Validate token format
    if not telegram_token.count(":") == 1:
        print("❌ TELEGRAM_BOT_TOKEN appears to be invalid")
        print("   Should be in format: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        return False

    print("✅ Environment variables configured")
    return True


def main():
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
        print("3. Run this script again")
        sys.exit(1)

    print("\n🚀 Starting bot...")
    print("=" * 40)

    # Import and run the main bot
    try:
        from main import main as bot_main

        # Don't use asyncio.run() - let main.py handle it
        if __name__ == "__main__":
            import asyncio

            asyncio.run(bot_main())
        else:
            # If called from another module, just call the function
            bot_main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        print("\nCheck the logs (torboxtg.log) for more details")
        sys.exit(1)


if __name__ == "__main__":
    main()
