#!/usr/bin/env python3
"""
TorboxTG - Telegram Bot for Debriding Terabox Links using Torbox API

This bot listens for messages with the prefix /tb followed by a Terabox link,
sends the link to Torbox for debriding, downloads the resulting file,
and uploads it to Telegram.
"""

import asyncio
import json
import logging
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Set
from urllib.parse import unquote, urlparse

import aiofiles
import aiohttp
from asyncio_throttle import Throttler
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("torboxtg.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL")  # Optional local Bot API server
TORBOX_API_TOKEN = os.getenv("TORBOX_API_TOKEN")
AUTH_KEY = os.getenv("AUTH_KEY")  # Authentication key
TORBOX_API_BASE = "https://api.torbox.app/v1/api"
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 2147483648))  # Default 2GB
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "3600"))  # 1 hour
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", "1800"))  # 30 minutes for uploads
TEMP_DIR = os.getenv("TEMP_DIR", tempfile.gettempdir())

# Rate limiting - more conservative to avoid flood control
throttler = Throttler(rate_limit=5, period=60)  # 5 requests per minute


class TorboxAPI:
    """Handles interactions with the Torbox API"""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def create_web_download(self, url: str) -> dict:
        """Create a web download for the given URL."""
        # Use form data instead of JSON
        form_data = aiohttp.FormData()
        form_data.add_field("link", url)

        # Remove Content-Type from headers for form data
        headers = {"Authorization": f"Bearer {self.api_token}"}

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{TORBOX_API_BASE}/webdl/createwebdownload",
                headers=headers,
                data=form_data,
            )
            if response.status == 200:
                result = await response.json()
                return result
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to create web download: {response.status} - {error_text}"
                )
                raise Exception(f"API Error: {response.status} - {error_text}")

    async def get_download_list(self) -> dict:
        """Get the list of web downloads."""
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{TORBOX_API_BASE}/webdl/mylist", headers=self.headers
            )
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to get download list: {response.status} - {error_text}"
                )
                raise Exception(f"API Error: {response.status} - {error_text}")

    async def get_download_info(self, web_id) -> dict:
        """Get info for a specific web download."""
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{TORBOX_API_BASE}/webdl/mylist?id={web_id}", headers=self.headers
            )
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to get download info: {response.status} - {error_text}"
                )
                raise Exception(f"API Error: {response.status} - {error_text}")

    async def request_download_link(self, web_id: int, file_id: int = None) -> str:
        """Request download link for a web download."""
        params = {"token": self.api_token, "web_id": web_id}
        if file_id:
            params["file_id"] = file_id

        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{TORBOX_API_BASE}/webdl/requestdl", headers=self.headers, params=params
            )
            if response.status == 200:
                result = await response.json()
                return result.get("data")
            else:
                error_text = await response.text()
                logger.error(
                    f"Failed to request download link: {response.status} - {error_text}"
                )
                raise Exception(f"API Error: {response.status} - {error_text}")


class TorboxTelegramBot:
    """Telegram bot for processing Terabox links"""

    def __init__(self, telegram_token: str, torbox_token: str):
        self.telegram_token = telegram_token
        self.torbox_token = torbox_token
        self.active_downloads = {}
        self.download_queue = []  # Queue for pending downloads
        self.max_concurrent_downloads = 2  # Limit to 2 concurrent downloads
        self.application = None
        self.authenticated_users: Set[int] = set()
        self.auth_file = "authenticated_users.json"
        self.load_authenticated_users()

    def load_authenticated_users(self):
        """Load authenticated users from file"""
        try:
            if Path(self.auth_file).exists():
                with open(self.auth_file, "r") as f:
                    user_list = json.load(f)
                    self.authenticated_users = set(user_list)
                logger.info(f"Loaded {len(self.authenticated_users)} authenticated users")
        except Exception as e:
            logger.error(f"Error loading authenticated users: {e}")
            self.authenticated_users = set()

    def save_authenticated_users(self):
        """Save authenticated users to file"""
        try:
            with open(self.auth_file, "w") as f:
                json.dump(list(self.authenticated_users), f)
        except Exception as e:
            logger.error(f"Error saving authenticated users: {e}")

    def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        return user_id in self.authenticated_users

    def authenticate_user(self, user_id: int):
        """Add user to authenticated list"""
        self.authenticated_users.add(user_id)
        self.save_authenticated_users()
        logger.info(f"User {user_id} authenticated successfully")

    def get_active_download_count(self) -> int:
        """Get the number of currently active downloads"""
        return len(
            [
                d
                for d in self.active_downloads.values()
                if d.get("status") not in ["completed", "failed", "error"]
            ]
        )

    def can_start_new_download(self) -> bool:
        """Check if we can start a new download without exceeding limits"""
        return self.get_active_download_count() < self.max_concurrent_downloads

    def add_to_queue(self, download_request: dict):
        """Add a download request to the queue"""
        self.download_queue.append(download_request)
        logger.info(f"Added download to queue. Queue size: {len(self.download_queue)}")

    def process_queue(self):
        """Process queued downloads if slots are available"""
        while self.download_queue and self.can_start_new_download():
            download_request = self.download_queue.pop(0)
            logger.info(
                f"Processing queued download. Remaining in queue: {len(self.download_queue)}"
            )
            # Start the download processing
            asyncio.create_task(self.process_queued_download(download_request))

    async def process_queued_download(self, download_request: dict):
        """Process a download request from the queue"""
        try:
            update = download_request["update"]
            link = download_request["link"]
            await self.process_terabox_link(update, link)
        except Exception as e:
            logger.error(f"Error processing queued download: {e}")
            # Try to send error message to user
            try:
                chat_id = download_request.get("update", {}).effective_chat.id
                await self.send_message_to_chat(
                    chat_id,
                    f"❌ **Error processing queued download**\n\n" f"Error: {str(e)}",
                )
            except Exception:
                pass

    def is_terabox_link(self, url: str) -> bool:
        """Check if the URL is a Terabox link"""
        terabox_domains = [
            "terabox.com",
            "1024terabox.com",
            "teraboxapp.com",
            "nephobox.com",
            "4funbox.com",
            "mirrobox.com",
            "momerybox.com",
            "teraboxlink.com",
            "terasharelink.com",
        ]

        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace("www.", "")
            return any(domain.endswith(tb_domain) for tb_domain in terabox_domains)
        except Exception:
            return False

    def extract_terabox_links(self, text: str) -> list:
        """Extract Terabox links from text"""
        # Pattern to match URLs
        url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        urls = re.findall(url_pattern, text)

        terabox_links = [url for url in urls if self.is_terabox_link(url)]
        return terabox_links

    def normalize_terabox_url(self, url: str) -> str:
        """
        Normalize alternative Terabox domains to terabox.com for Torbox API compatibility.
        Torbox API only supports terabox.com domain.
        """
        if not self.is_terabox_link(url):
            return url

        try:
            parsed = urlparse(url)

            # Alternative domains that should be converted to terabox.com
            alternative_domains = [
                "1024terabox.com",
                "teraboxapp.com",
                "nephobox.com",
                "4funbox.com",
                "mirrobox.com",
                "momerybox.com",
                "teraboxlink.com",
                "terasharelink.com",
            ]

            current_domain = parsed.netloc.replace("www.", "").lower()

            # If it's an alternative domain, convert to terabox.com
            for alt_domain in alternative_domains:
                if current_domain.endswith(alt_domain):
                    # Reconstruct URL with terabox.com domain
                    new_url = f"{parsed.scheme}://terabox.com{parsed.path}"
                    if parsed.query:
                        new_url += f"?{parsed.query}"
                    if parsed.fragment:
                        new_url += f"#{parsed.fragment}"

                    logger.info(f"Normalized URL: {url} -> {new_url}")
                    return new_url

            # If it's already terabox.com, return as is
            return url

        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {e}")
            return url

    def get_chat_type(self, update: Update) -> str:
        """Get the type of chat (private, group, supergroup, channel)"""
        return update.effective_chat.type

    def is_private_chat(self, update: Update) -> bool:
        """Check if the message is from a private chat"""
        return self.get_chat_type(update) == "private"

    def is_group_chat(self, update: Update) -> bool:
        """Check if the message is from a group or supergroup"""
        return self.get_chat_type(update) in ["group", "supergroup"]

    def should_respond_to_message(self, update: Update, message_text: str) -> bool:
        """Determine if bot should respond to a message based on chat type and content"""
        if self.is_private_chat(update):
            # In private chats, respond to authenticated users
            return self.is_user_authenticated(update.effective_user.id)

        if self.is_group_chat(update):
            # In groups, automatically respond to any message containing Terabox links
            terabox_links = self.extract_terabox_links(message_text)
            if terabox_links:
                return True

            # Also respond to /tb commands for backward compatibility
            if message_text.startswith("/tb"):
                return True

            # Check if bot is mentioned
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == "mention":
                        mention = message_text[
                            entity.offset : entity.offset + entity.length
                        ]
                        bot_username = f"@{update.get_bot().username.lower()}"
                        if mention.lower() == bot_username:
                            return True

            # Check if it's a reply to the bot
            if (
                update.message.reply_to_message
                and update.message.reply_to_message.from_user.id == update.get_bot().id
            ):
                return True

        return False

    async def auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /auth command for user authentication"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # Check if AUTH_KEY is set
        if not AUTH_KEY:
            await update.message.reply_text(
                "❌ **Authentication not configured**\n\n" "Contact the bot administrator.",
                parse_mode="Markdown",
            )
            return

        # Extract the key from the command
        parts = message_text.split()
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ **Invalid format**\n\n" "Usage: `/auth <key>`", parse_mode="Markdown"
            )
            # Delete the user's message to protect the key
            try:
                await update.message.delete()
            except Exception:
                pass
            return

        provided_key = parts[1]

        # Check if the key is correct
        if provided_key != AUTH_KEY:
            await update.message.reply_text(
                "❌ **Invalid authentication key**\n\n" "Access denied.",
                parse_mode="Markdown",
            )
            # Delete the user's message to protect the attempted key
            try:
                await update.message.delete()
            except Exception:
                pass
            return

        # Authenticate the user
        self.authenticate_user(user_id)

        # Send success message
        success_msg = await update.message.reply_text(
            "✅ **Authentication successful!**\n\n" "You can now use the bot. Welcome!",
            parse_mode="Markdown",
        )

        # Delete both the auth command message and success message after a delay
        try:
            await update.message.delete()
            await asyncio.sleep(5)  # Wait 5 seconds then delete success message
            await success_msg.delete()
        except Exception:
            pass

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id

        # Check authentication first
        if not self.is_user_authenticated(user_id):
            await update.message.reply_text(
                "🔐 **Authentication Required**\n\n"
                "Please authenticate first using:\n"
                "```\n/auth <your_key>\n```\n\n"
                "Contact the bot administrator if you don't have a key.",
                parse_mode="Markdown",
            )
            return

        chat_type = self.get_chat_type(update)
        user_name = update.effective_user.first_name or "User"

        if chat_type == "private":
            welcome_message = f"""
🤖 **Welcome to TorboxTG Bot, {user_name}!**

I'm a specialized Terabox debriding bot using the Torbox API.

**How to use:**
• Simply send or forward any message with Terabox links
• I'll automatically detect and process all links
• Multiple links in one message? I'll handle them all!
• Use `/status` to check active downloads

**Features:**
- ⚡ Automatic Terabox link detection
- 🔗 Multiple links processing
- 📁 Fast processing through Torbox API
- 🎬 Automatic file type detection
- 📊 Real-time progress updates
- 🌍 Supports all Terabox domains

Type /help for more information.
            """
        else:
            welcome_message = f"""
🤖 **TorboxTG Bot added to {update.effective_chat.title}!**

Hello everyone! I'm a specialized Terabox debriding bot.

**How it works:**
• Just send or forward messages with Terabox links to this group
• I'll automatically detect and process all Terabox links
• No commands needed - fully automatic!
• Multiple links? I'll process them all!

**Features:**
- ⚡ Automatic Terabox link detection
- 🔗 Multiple links processing in one message
- 📁 Fast processing through Torbox API
- 🎬 Works with all file types
- 📊 Real-time progress updates

Type /help for more information.
            """

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id

        # Check authentication first
        if not self.is_user_authenticated(user_id):
            await update.message.reply_text(
                "🔐 **Authentication Required**\n\n"
                "Please authenticate first using:\n"
                "```\n/auth <your_key>\n```\n\n"
                "Contact the bot administrator if you don't have a key.",
                parse_mode="Markdown",
            )
            return

        chat_type = self.get_chat_type(update)

        if chat_type == "private":
            help_message = """
📖 **Help & Commands**

**Commands:**
• `/auth <key>` - Authenticate to use the bot
• `/start` - Show welcome message
• `/help` - Show this help
• `/status` - Check your active downloads

**How to Use:**
• Simply send or paste any message containing Terabox links
• Forward messages with Terabox links from other chats
• I automatically detect and process ALL links in your message
• No commands needed - just send the links!

**Usage Examples:**
• Send: `Check this out: https://terabox.com/s/1234567890abcdef`
• Forward a message containing Terabox links
• Send multiple links: `Link 1: [url1] and Link 2: [url2]`

**Supported Domains:**
• Terabox.com • 1024terabox.com • Teraboxapp.com
• Nephobox.com • 4funbox.com • Mirrobox.com
• Momerybox.com • Teraboxlink.com • Terasharelink.com

**Features:**
• ⚡ Automatic link detection - no commands needed
• 🔗 Multiple links processing in one message
• 📁 All file types supported (videos, documents, archives, etc.)
• 🌍 All Terabox domains automatically converted for compatibility

**Limitations:**
• Max file size: 2GB per file
• Processing time: Up to 1 hour per file
• Authentication required for private chat

**Tips:**
• Make sure Terabox links are public and accessible
• Large files may take longer to process
• Check /status for download progress
            """
        else:
            help_message = f"""
📖 **Help & Commands (Group Chat)**

**Commands:**
• `/auth <key>` - Authenticate to use the bot
• `/start` - Show welcome message
• `/help` - Show this help
• `/tb <link>` - Debrid a Terabox link
• `/status` - Check your active downloads

**Group Usage:**
• Use `/tb <link>` command
• Mention me: `@{context.bot.username} <terabox_link>`
• Reply to my messages with Terabox links

**Supported Links:**
• Terabox.com • 1024terabox.com • Teraboxapp.com
• Nephobox.com • 4funbox.com • Mirrobox.com
• And other Terabox domains

**Note:** All alternative domains are automatically converted to terabox.com for API compatibility.

**Group Features:**
• Only responds when mentioned or with /tb command
• Processes links for the user who requested
• Sends files to the group chat

**Limitations:**
• Max file size: 2GB • Processing time: Up to 1 hour
• Terabox links must be public and accessible
            """

        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id

        # Check authentication first
        if not self.is_user_authenticated(user_id):
            await update.message.reply_text(
                "🔐 **Authentication Required**\n\n"
                "Please authenticate first using:\n"
                "```\n/auth <your_key>\n```\n\n"
                "Contact the bot administrator if you don't have a key.",
                parse_mode="Markdown",
            )
            return

        user_id_str = str(user_id)
        user_downloads = {
            k: v
            for k, v in self.active_downloads.items()
            if v.get("user_id") == user_id_str
        }

        # Check user's queued downloads
        user_queued = [
            req
            for req in self.download_queue
            if str(req.get("update", {}).effective_user.id) == user_id_str
        ]

        if not user_downloads and not user_queued:
            await update.message.reply_text("📭 You have no active or queued downloads.")
            return

        chat_type = self.get_chat_type(update)
        user_name = update.effective_user.first_name or "User"

        if chat_type == "private":
            status_message = "📊 **Your Download Status:**\n\n"
        else:
            status_message = f"📊 **{user_name}'s Download Status:**\n\n"

        # Add queue summary
        status_message += f"🔄 Active: {len(user_downloads)}\n"
        status_message += f"⏳ Queued: {len(user_queued)}\n"
        status_message += f"📊 System: {self.get_active_download_count()}/{self.max_concurrent_downloads} active\n\n"

        for download_id, info in user_downloads.items():
            status_message += f"🔗 **{info.get('filename', 'Unknown')}**\n"
            status_message += f"Status: {info.get('status', 'Unknown')}\n"
            status_message += f"Progress: {info.get('progress', 'N/A')}\n"
            status_message += f"Started: {info.get('started_at', 'N/A')}\n\n"

        await update.message.reply_text(status_message, parse_mode="Markdown")

    async def handle_tb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tb command with Terabox link"""
        user_id = update.effective_user.id

        # Check authentication first
        if not self.is_user_authenticated(user_id):
            await update.message.reply_text(
                "🔐 **Authentication Required**\n\n"
                "Please authenticate first using:\n"
                "```\n/auth <your_key>\n```\n\n"
                "Contact the bot administrator if you don't have a key.",
                parse_mode="Markdown",
            )
            return

        if not context.args:
            chat_type = self.get_chat_type(update)
            if chat_type == "private":
                error_msg = (
                    "❌ Please provide a Terabox link!\n\n"
                    "Usage: `/tb <terabox_link>`\n"
                    "Example: `/tb https://terabox.com/s/1234567890abcdef`"
                )
            else:
                error_msg = (
                    "❌ Please provide a Terabox link!\n\n"
                    "Usage: `/tb <terabox_link>`\n"
                    f"Example: `/tb https://terabox.com/s/1234567890abcdef`\n"
                    f"Or mention me: `@{context.bot.username} <terabox_link>`"
                )

            await update.message.reply_text(error_msg, parse_mode="Markdown")
            return

        link = " ".join(context.args)

        if not self.is_terabox_link(link):
            await update.message.reply_text(
                "❌ This doesn't appear to be a valid Terabox link.\n\n"
                "Supported domains: terabox.com, 1024terabox.com, teraboxapp.com, etc."
            )
            return

        await self.process_terabox_link(update, link)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages that might contain Terabox links"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id

        # Check authentication first
        if not self.is_user_authenticated(user_id):
            # Only respond with auth message if this looks like a command or terabox link
            text = update.message.text
            if (
                text.startswith("/")
                or self.extract_terabox_links(text)
                or self.should_respond_to_message(update, text)
            ):
                await update.message.reply_text(
                    "🔐 **Authentication Required**\n\n"
                    "Please authenticate first using:\n"
                    "```\n/auth <your_key>\n```\n\n"
                    "Contact the bot administrator if you don't have a key.",
                    parse_mode="Markdown",
                )
            return

        text = update.message.text

        # Check if we should respond to this message
        if not self.should_respond_to_message(update, text):
            return

        # Check if message starts with /tb (alternative to command handler)
        if text.startswith("/tb "):
            link = text[4:].strip()
            if self.is_terabox_link(link):
                await self.process_terabox_link(update, link)
            else:
                await update.message.reply_text(
                    "❌ Invalid Terabox link. Please check the URL and try again."
                )
            return

        # Extract Terabox links from the message
        terabox_links = self.extract_terabox_links(text)

        if terabox_links:
            user_name = update.effective_user.first_name or "User"
            chat_title = update.effective_chat.title or "group"

            # Show initial message for multiple links
            if len(terabox_links) > 1:
                if self.is_group_chat(update):
                    initial_msg = await update.message.reply_text(
                        f"🔗 **Found {len(terabox_links)} Terabox links from "
                        f"{user_name}**\n\n"
                        f"📋 Processing all links in {chat_title}...\n"
                        f"⏳ This may take a few moments",
                        parse_mode="Markdown",
                    )
                else:
                    initial_msg = await update.message.reply_text(
                        f"🔗 **Found {len(terabox_links)} Terabox links**\n\n"
                        f"📋 Processing all links...\n"
                        f"⏳ This may take a few moments",
                        parse_mode="Markdown",
                    )

                # Small delay to show the message
                await asyncio.sleep(2)
                await initial_msg.delete()

                # Process all Terabox links found in the message
            for i, link in enumerate(terabox_links, 1):
                if self.can_start_new_download():
                    # Process immediately if we have available slots
                    if len(terabox_links) > 1 and i > 1:
                        await asyncio.sleep(1)  # Small delay for multiple links
                    await self.process_terabox_link(update, link)
                else:
                    # Add to queue if we've reached the limit
                    queue_position = len(self.download_queue) + 1
                    self.add_to_queue({"update": update, "link": link})

                    # Notify user about queueing
                    link_preview = link[:50] + ("..." if len(link) > 50 else "")
                    await update.message.reply_text(
                        f"⏳ **Download Queued** (Position: {queue_position})\n\n"
                        f"🔗 Link: `{link_preview}`\n"
                        f"📊 Active downloads: {self.get_active_download_count()}/{self.max_concurrent_downloads}\n"
                        f"🎯 Your download will start automatically when a slot becomes available.",
                        parse_mode="Markdown",
                    )

    async def process_terabox_link(self, update: Update, link: str):
        """Process a Terabox link"""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "User"
        chat_type = self.get_chat_type(update)

        # Customize initial message based on chat type
        if chat_type == "private":
            initial_text = (
                "🔄 **Processing Terabox link...**\n\n"
                "⏳ Sending to Torbox for processing\n"
                "📡 This may take a few moments"
            )
        else:
            initial_text = (
                f"🔄 **Processing Terabox link for {user_name}...**\n\n"
                "⏳ Sending to Torbox for processing\n"
                "📡 This may take a few moments"
            )

        # Send initial processing message
        processing_msg = await update.message.reply_text(
            initial_text,
            parse_mode="Markdown",
        )

        try:
            torbox = TorboxAPI(self.torbox_token)
            # Create web download
            await processing_msg.edit_text(
                f"🔄 **Processing Terabox link{' for ' + user_name if chat_type != 'private' else ''}...**\n\n"
                "✅ Sending to Torbox\n"
                "⏳ Creating download request",
                parse_mode="Markdown",
            )

            normalized_link = self.normalize_terabox_url(link)
            result = await torbox.create_web_download(normalized_link)

            # Debug: Log the actual API response
            logger.info(f"API Response: {result}")

            if not result.get("success"):
                await processing_msg.edit_text(
                    f"❌ **Failed to create download**\n\n"
                    f"Error: {result.get('detail', 'Unknown error')}"
                )
                return

            download_data = result.get("data", {})
            download_id = download_data.get("webdownload_id")  # Fixed: use webdownload_id

            # Debug: Log download data structure
            logger.info(f"Download data: {download_data}")
            logger.info(f"Download ID: {download_id}")

            if not download_id:
                await processing_msg.edit_text("❌ **Failed to get download ID**")
                return

            # Check if this is a cached download
            detail = result.get("detail", "")
            is_cached = "cached" in detail.lower()

            # Store download info
            self.active_downloads[download_id] = {
                "user_id": user_id,
                "user_name": user_name,
                "link": link,
                "status": "cached" if is_cached else "processing",
                "started_at": str(asyncio.get_event_loop().time()),
                "message_id": processing_msg.message_id,
                "chat_id": update.effective_chat.id,
                "chat_type": chat_type,
            }

            if is_cached:
                await processing_msg.edit_text(
                    f"⚡ **Found Cached Download!{' for ' + user_name if chat_type != 'private' else ''}**\n\n"
                    "✅ File already processed by Torbox\n"
                    "🔍 Checking download status...",
                    parse_mode="Markdown",
                )
                # For cached downloads, check status immediately
                asyncio.create_task(self.check_cached_download(download_id))
            else:
                await processing_msg.edit_text(
                    f"🔄 **Download Created Successfully!"
                    f"{' for ' + user_name if chat_type != 'private' else ''}**\n\n"
                    "✅ Request sent to Torbox\n"
                    "⏳ Waiting for processing to complete\n"
                    "🔍 Checking status...",
                    parse_mode="Markdown",
                )
                # Start monitoring the download
                asyncio.create_task(self.monitor_download(download_id))

        except Exception as e:
            error_str = str(e)
            logger.error(f"Error processing Terabox link: {e}")

            # Check if it's an ACTIVE_LIMIT error
            if "ACTIVE_LIMIT" in error_str:
                # Add to queue instead of failing
                queue_position = len(self.download_queue) + 1
                self.add_to_queue({"update": update, "link": link})

                link_preview = link[:50] + ("..." if len(link) > 50 else "")
                await processing_msg.edit_text(
                    f"⏳ **Download Queued** (Position: {queue_position})\n\n"
                    f"🔗 Link: `{link_preview}`\n"
                    f"📊 Active downloads: {self.get_active_download_count()}/{self.max_concurrent_downloads}\n"
                    f"🎯 Reached concurrent download limit. Your download will start automatically when a slot becomes available.",
                    parse_mode="Markdown",
                )
            else:
                await processing_msg.edit_text(
                    f"❌ **Error processing link**\n\n"
                    f"Error: {error_str}\n\n"
                    "Please try again or contact support."
                )

    async def check_cached_download(self, download_id: str):
        """Check if cached download is ready immediately"""
        try:
            torbox = TorboxAPI(self.torbox_token)
            info = await torbox.get_download_info(download_id)

            if not info.get("success"):
                logger.error(f"Failed to get info for cached download {download_id}")
                # Fall back to regular monitoring
                await self.monitor_download(download_id)
                return

            download_data = info.get("data", {})
            logger.info(f"Cached download {download_id} data structure: {download_data}")

            # API uses 'download_state' field, not 'status'
            status = download_data.get("download_state", "").lower()
            logger.info(f"Cached download {download_id} status: '{status}'")

            if status == "completed":
                # Cached download is ready, handle completion immediately
                logger.info(f"Cached download {download_id} is ready, handling completion")
                await self.handle_download_complete(download_id, download_data)
            else:
                # For cached downloads, they might be ready even without "completed" status
                # Check if we have files available
                files = download_data.get("files", [])
                if files:
                    logger.info(
                        f"Cached download {download_id} has files available, handling completion"
                    )
                    await self.handle_download_complete(download_id, download_data)
                else:
                    # Cached download is not ready yet, monitor normally
                    logger.info(
                        f"Cached download {download_id} not ready "
                        f"(status: '{status}', no files), starting monitoring"
                    )
                    await self.monitor_download(download_id)

        except Exception as e:
            logger.error(f"Error checking cached download {download_id}: {e}")
            # Fall back to regular monitoring
            await self.monitor_download(download_id)

    async def monitor_download(self, download_id: str):
        """Monitor download progress and handle completion"""
        max_attempts = 720  # Monitor for up to 1 hour (720 attempts * 5 seconds)
        attempt = 0
        last_status = None
        last_progress = None

        while attempt < max_attempts:
            try:
                torbox = TorboxAPI(self.torbox_token)
                info = await torbox.get_download_info(download_id)

                if not info.get("success"):
                    logger.error(f"Failed to get download info for {download_id}")
                    break

                download_data = info.get("data", {})
                # API uses 'download_state' field, not 'status'
                status = download_data.get("download_state", "").lower()
                progress = download_data.get("progress", 0)

                # Debug: Log the monitoring response structure with progress
                logger.info(
                    f"Monitor download {download_id} - Status: '{status}', Progress: {progress}, Data: {download_data}"
                )

                # Update stored info
                if download_id in self.active_downloads:
                    self.active_downloads[download_id]["status"] = status
                    self.active_downloads[download_id]["progress"] = progress
                    self.active_downloads[download_id]["download_data"] = download_data

                if status == "completed":
                    logger.info(f"Download {download_id} completed, handling completion")
                    await self.handle_download_complete(download_id, download_data)
                    break
                elif status in ["failed", "error"]:
                    logger.info(f"Download {download_id} failed with status: {status}")
                    await self.handle_download_failed(download_id, download_data)
                    break

                # Update progress message when status changes or progress changes significantly
                status_changed = last_status != status
                progress_changed = (
                    last_progress is None
                    or abs(progress - last_progress)
                    >= 0.1  # 10% change (reduced frequency)
                )

                # Also update every 24 attempts (2 minutes) for active downloads (reduced frequency)
                if (
                    status_changed or progress_changed or attempt % 24 == 0
                ) and download_id in self.active_downloads:
                    await self.update_progress_message(download_id, status, download_data)
                    last_status = status
                    last_progress = progress

                await asyncio.sleep(5)  # Wait 5 seconds before next check
                attempt += 1

            except Exception as e:
                logger.error(f"Error monitoring download {download_id}: {e}")
                await asyncio.sleep(5)
                attempt += 1

        # If we've reached max attempts, notify timeout
        if attempt >= max_attempts and download_id in self.active_downloads:
            await self.handle_download_timeout(download_id)

    async def update_progress_message(
        self, download_id: str, status: str, download_data: dict = None
    ):
        """Update the progress message with detailed progress information"""
        if download_id not in self.active_downloads:
            return

        download_info = self.active_downloads[download_id]
        chat_id = download_info.get("chat_id")
        message_id = download_info.get("message_id")

        if not chat_id or not message_id:
            return

        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "downloading": "⬇️",
            "downloaded": "✅",
            "completed": "✅",
            "failed": "❌",
            "error": "❌",
        }

        emoji = status_emoji.get(status, "🔄")

        # Get progress information
        progress = download_info.get("progress", 0)
        progress_percent = int(progress * 100) if isinstance(progress, (int, float)) else 0

        # Create progress bar
        progress_bar = self.create_progress_bar(progress_percent)

        # Get file size and download speed if available
        size_info = ""
        speed_info = ""
        eta_info = ""

        if download_data:
            file_size = download_data.get("size", 0)
            if file_size > 0:
                size_info = f"📊 Size: {self.format_file_size(file_size)}\n"

            download_speed = download_data.get("download_speed", 0)
            if download_speed > 0:
                speed_info = f"⚡ Speed: {self.format_file_size(download_speed)}/s\n"

            eta = download_data.get("eta", 0)
            if eta > 0:
                eta_min = int(eta / 60)
                eta_sec = eta % 60
                eta_info = f"⏱️ ETA: {eta_min}m {eta_sec}s\n"

        try:
            # Use throttler and update message via our rate-limited function
            await self.update_message_in_chat(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{emoji} **Download Status: {status.title()}**\n\n"
                f"🔗 Processing your Terabox link\n"
                f"{size_info}"
                f"{speed_info}"
                f"{eta_info}"
                f"📈 Progress: {progress_percent}%\n"
                f"{progress_bar}\n"
                f"⏱️ Updates every 10 seconds",
            )
        except Exception as e:
            logger.error(f"Failed to update progress message: {e}")

    def create_progress_bar(self, percentage: int) -> str:
        """Create a visual progress bar"""
        filled = int(percentage / 10)  # Each block represents 10%
        empty = 10 - filled
        return "█" * filled + "░" * empty + f" {percentage}%"

    async def handle_download_complete(self, download_id: str, download_data: Dict):
        """Handle completed download"""
        if download_id not in self.active_downloads:
            return

        download_info = self.active_downloads[download_id]
        chat_id = download_info.get("chat_id")
        message_id = download_info.get("message_id")

        try:
            files = download_data.get("files", [])
            if not files:
                await self.send_message_to_chat(
                    chat_id, "❌ **No files found in the download**"
                )
                return

            # Get the first (and usually only) file
            file_info = files[0]
            file_name = file_info.get("name", "download")
            file_size = file_info.get("size", 0)

            # Get effective file size limits based on API server type
            video_limit, document_limit = self.get_effective_file_limits()

            is_video = self.is_video_file(file_name)
            effective_limit = video_limit if is_video else document_limit

            if file_size > effective_limit:
                file_type = "video" if is_video else "document"
                await self.send_message_to_chat(
                    chat_id,
                    f"❌ **File too large for {file_type} upload**\n\n"
                    f"📁 {file_name}\n"
                    f"📊 Size: {self.format_file_size(file_size)}\n"
                    f"⚠️ Maximum for {file_type}s: {self.format_file_size(effective_limit)}\n\n"
                    f"💡 Try downloading smaller files or use a different service.",
                )
                return

            # Request download link
            torbox = TorboxAPI(self.torbox_token)
            link_result = await torbox.request_download_link(
                download_id, str(file_info.get("id"))
            )

            if not link_result:
                await self.send_message_to_chat(
                    chat_id, "❌ **Failed to get download link**"
                )
                return

            download_url = link_result
            if not download_url:
                await self.send_message_to_chat(
                    chat_id, "❌ **Invalid download link received**"
                )
                return

            # Update status message
            await self.update_message_in_chat(
                chat_id,
                message_id,
                "⬇️ **Downloading file to server...**\n\n"
                f"📁 {file_name}\n"
                f"📊 Size: {self.format_file_size(file_size)}\n"
                "⏳ Please wait...",
            )

            # Download and upload file
            await self.download_and_upload_file(chat_id, download_url, file_name, file_size)

        except Exception as e:
            logger.error(f"Error handling download completion: {e}")
            await self.send_message_to_chat(
                chat_id, f"❌ **Error processing download**\n\nError: {str(e)}"
            )

        finally:
            # Clean up
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
                # Process queue after completing a download
                self.process_queue()

    async def download_and_upload_file(
        self, chat_id: int, download_url: str, filename: str, file_size: int
    ):
        """Download file and upload to Telegram"""
        import asyncio

        temp_file_path = None

        try:
            # Sanitize filename for safe path construction
            safe_filename = "".join(
                c for c in filename if c.isalnum() or c in ".-_"
            ).rstrip()
            if not safe_filename:
                safe_filename = "download"

            # Create temporary file with safe filename
            timestamp = str(int(asyncio.get_event_loop().time()))
            temp_filename = f"torboxtg_{timestamp}_{safe_filename}"
            temp_file_path = Path(TEMP_DIR) / temp_filename

            logger.info(f"Downloading file to: {temp_file_path}")

            # Ensure temp directory exists
            temp_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed with status {response.status}")

                    async with aiofiles.open(temp_file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

            # Verify file exists and has content
            if not temp_file_path.exists():
                raise Exception("Downloaded file does not exist")

            actual_size = temp_file_path.stat().st_size
            if actual_size == 0:
                raise Exception("Downloaded file is empty")

            logger.info(f"File downloaded successfully. Size: {actual_size} bytes")

            # Upload to Telegram using proper context managers with timeout
            try:
                if self.is_video_file(filename):
                    with open(temp_file_path, "rb") as video_file:
                        await asyncio.wait_for(
                            self.application.bot.send_video(
                                chat_id=chat_id,
                                video=video_file,
                                caption=f"**{filename}**\nSize: {self.format_file_size(file_size)}",
                                parse_mode="Markdown",
                                supports_streaming=True,
                                read_timeout=UPLOAD_TIMEOUT,
                                write_timeout=UPLOAD_TIMEOUT,
                                connect_timeout=UPLOAD_TIMEOUT,
                                pool_timeout=UPLOAD_TIMEOUT,
                            ),
                            timeout=UPLOAD_TIMEOUT,
                        )
                else:
                    with open(temp_file_path, "rb") as document_file:
                        await asyncio.wait_for(
                            self.application.bot.send_document(
                                chat_id=chat_id,
                                document=document_file,
                                caption=f"**{filename}**\nSize: {self.format_file_size(file_size)}",
                                parse_mode="Markdown",
                                read_timeout=UPLOAD_TIMEOUT,
                                write_timeout=UPLOAD_TIMEOUT,
                                connect_timeout=UPLOAD_TIMEOUT,
                                pool_timeout=UPLOAD_TIMEOUT,
                            ),
                            timeout=UPLOAD_TIMEOUT,
                        )
            except asyncio.TimeoutError:
                logger.error(f"Upload timed out after {UPLOAD_TIMEOUT}s: {filename}")
                await self.send_message_to_chat(
                    chat_id,
                    f"⏰ **Upload Timeout**\n\n"
                    f"📁 {filename}\n"
                    f"📊 Size: {self.format_file_size(actual_size)}\n\n"
                    f"🔍 Upload took longer than {UPLOAD_TIMEOUT // 60} minutes.\n"
                    f"💡 This may be due to slow upload speed or network issues.\n"
                    f"🛠️ Try increasing UPLOAD_TIMEOUT in your .env file or use a faster connection.",
                )
                return
            except Exception as upload_error:
                error_msg = str(upload_error)
                if "413" in error_msg or "Entity Too Large" in error_msg:
                    await self.send_message_to_chat(
                        chat_id,
                        f"❌ **File too large for Telegram**\n\n"
                        f"📁 {filename}\n"
                        f"📊 Size: {self.format_file_size(actual_size)}\n\n"
                        f"🔍 The file exceeds Telegram's practical upload limits.\n"
                        f"💡 Try downloading a smaller file or split large files.",
                    )
                    return
                else:
                    # Re-raise other upload errors to be handled by outer try-catch
                    raise upload_error

            await self.send_message_to_chat(
                chat_id, "✅ **Upload completed successfully!**"
            )

        except Exception as e:
            logger.error(f"Error downloading/uploading file: {e}")
            await self.send_message_to_chat(
                chat_id, f"❌ **Upload failed**\n\nError: {str(e)}"
            )

        finally:
            # Clean up temporary file
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.info(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete temp file: {e}")

    async def handle_download_failed(self, download_id: str, download_data: Dict):
        """Handle failed download"""
        if download_id not in self.active_downloads:
            return

        download_info = self.active_downloads[download_id]
        chat_id = download_info.get("chat_id")

        error_msg = download_data.get("error", "Unknown error")

        await self.send_message_to_chat(
            chat_id,
            f"❌ **Download Failed**\n\n"
            f"Error: {error_msg}\n\n"
            "Please check your link and try again.",
        )

        # Clean up
        if download_id in self.active_downloads:
            del self.active_downloads[download_id]
            # Process queue after handling failed download
            self.process_queue()

    async def handle_download_timeout(self, download_id: str):
        """Handle download timeout"""
        if download_id not in self.active_downloads:
            return

        download_info = self.active_downloads[download_id]
        chat_id = download_info.get("chat_id")

        await self.send_message_to_chat(
            chat_id,
            "⏰ **Download Timeout**\n\n"
            "The download took too long to complete.\n"
            "Please try again with a smaller file or check your link.",
        )

        # Clean up
        if download_id in self.active_downloads:
            del self.active_downloads[download_id]
            # Process queue after handling timeout
            self.process_queue()

    async def send_message_to_chat(self, chat_id: int, message: str) -> None:
        """Send a message to a specific chat with rate limiting."""
        try:
            # Use throttler to respect rate limits
            async with throttler:
                await self.application.bot.send_message(
                    chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            error_msg = str(e).lower()
            if "flood control" in error_msg or "too many requests" in error_msg:
                logger.warning(f"Rate limited when sending message, skipping: {e}")
            else:
                logger.error(f"Failed to send message: {e}")

    async def send_document_to_chat(
        self, chat_id: int, file_path: Path, caption: str = None
    ) -> None:
        """Send a document to a specific chat."""
        try:
            logger.info(f"Starting document upload: {file_path.name}")

            # Set longer timeout for large files
            import asyncio

            with open(file_path, "rb") as f:
                await asyncio.wait_for(
                    self.application.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        read_timeout=UPLOAD_TIMEOUT,
                        write_timeout=UPLOAD_TIMEOUT,
                        connect_timeout=UPLOAD_TIMEOUT,
                        pool_timeout=UPLOAD_TIMEOUT,
                    ),
                    timeout=UPLOAD_TIMEOUT,
                )
            logger.info(f"Document upload completed: {file_path.name}")

        except asyncio.TimeoutError:
            logger.error(
                f"Document upload timed out after {UPLOAD_TIMEOUT}s: {file_path.name}"
            )
            raise Exception(f"Upload timed out after {UPLOAD_TIMEOUT // 60} minutes")
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            raise

    async def send_video_to_chat(
        self, chat_id: int, file_path: Path, caption: str = None
    ) -> None:
        """Send a video to a specific chat."""
        try:
            logger.info(f"Starting video upload: {file_path.name}")

            # Set longer timeout for large files
            import asyncio

            with open(file_path, "rb") as f:
                await asyncio.wait_for(
                    self.application.bot.send_video(
                        chat_id=chat_id,
                        video=f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        read_timeout=UPLOAD_TIMEOUT,
                        write_timeout=UPLOAD_TIMEOUT,
                        connect_timeout=UPLOAD_TIMEOUT,
                        pool_timeout=UPLOAD_TIMEOUT,
                    ),
                    timeout=UPLOAD_TIMEOUT,
                )
            logger.info(f"Video upload completed: {file_path.name}")

        except asyncio.TimeoutError:
            logger.error(
                f"Video upload timed out after {UPLOAD_TIMEOUT}s: {file_path.name}"
            )
            raise Exception(f"Upload timed out after {UPLOAD_TIMEOUT // 60} minutes")
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
            raise

    async def update_message_in_chat(self, chat_id: int, message_id: int, text: str):
        """Update a specific message in a chat with rate limiting"""
        try:
            # Use throttler to respect rate limits
            async with throttler:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown"
                )
        except Exception as e:
            error_msg = str(e).lower()
            if "flood control" in error_msg or "too many requests" in error_msg:
                # Extract retry time if available
                import re

                retry_match = re.search(r"retry in (\d+)", error_msg)
                retry_seconds = int(retry_match.group(1)) if retry_match else 10

                logger.warning(
                    f"Rate limited, retrying message update in {retry_seconds} seconds"
                )
                await asyncio.sleep(retry_seconds + 1)  # Add 1 second buffer

                # Retry once after waiting
                try:
                    async with throttler:
                        await self.application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=text,
                            parse_mode="Markdown",
                        )
                except Exception as retry_error:
                    logger.error(
                        f"Failed to update message {message_id} after retry: {retry_error}"
                    )
            else:
                logger.error(
                    f"Failed to update message {message_id} in chat {chat_id}: {e}"
                )

    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        video_extensions = {
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
        }
        return Path(filename).suffix.lower() in video_extensions

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_effective_file_limits(self) -> tuple[int, int]:
        """Get effective file size limits based on API server type"""
        if TELEGRAM_API_URL:
            # Local Bot API server - much higher limits
            video_limit = int(2 * 1024 * 1024 * 1024)  # 2GB for videos
            document_limit = int(2 * 1024 * 1024 * 1024)  # 2GB for documents
            logger.info("Using local Bot API server - higher file limits enabled")
        else:
            # Official Telegram API - conservative limits
            video_limit = int(1.5 * 1024 * 1024 * 1024)  # 1.5GB for videos
            document_limit = int(1.9 * 1024 * 1024 * 1024)  # 1.9GB for documents
            logger.info("Using official Telegram API - standard file limits")

        return video_limit, document_limit

    def create_application(self) -> Application:
        """Create and configure the Telegram application"""
        if self.application is None:
            builder = Application.builder().token(self.telegram_token)

            # Configure local Bot API server if provided
            if TELEGRAM_API_URL:
                # Remove any trailing slash and ensure proper format
                api_url = TELEGRAM_API_URL.rstrip("/")
                builder = builder.base_url(f"{api_url}/bot")
                builder = builder.base_file_url(f"{api_url}/file/bot")
                logger.info(f"Configured local Bot API server: {api_url}")

            self.application = builder.build()

            # Add handlers
            self.application.add_handler(CommandHandler("auth", self.auth_command))
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("tb", self.handle_tb_command))
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )

        return self.application


def main():
    """Main function to run the bot"""
    # Validate environment variables
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return

    if not TORBOX_API_TOKEN:
        logger.error("TORBOX_API_TOKEN not found in environment variables")
        return

    if not AUTH_KEY:
        logger.error("AUTH_KEY not found in environment variables")
        logger.error("Please set an authentication key to secure your bot")
        return

    # Create bot instance
    bot = TorboxTelegramBot(TELEGRAM_BOT_TOKEN, TORBOX_API_TOKEN)

    # Create application
    application = bot.create_application()

    logger.info("TorboxTG Bot starting...")
    logger.info(f"Temp directory: {TEMP_DIR}")

    # Log API server configuration
    if TELEGRAM_API_URL:
        logger.info(f"Using local Telegram Bot API server: {TELEGRAM_API_URL}")
        video_limit, document_limit = bot.get_effective_file_limits()
        logger.info(f"Video upload limit: {bot.format_file_size(video_limit)}")
        logger.info(f"Document upload limit: {bot.format_file_size(document_limit)}")
    else:
        logger.info("Using official Telegram Bot API (api.telegram.org)")
        video_limit, document_limit = bot.get_effective_file_limits()
        logger.info(f"Video upload limit: {bot.format_file_size(video_limit)}")
        logger.info(f"Document upload limit: {bot.format_file_size(document_limit)}")

    try:
        # Start the bot with polling - this handles the event loop internally
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
