# 🤖 TorboxTG Bot

A powerful, enterprise-grade Telegram bot that debrids Terabox links using the Torbox API and delivers files directly to your Telegram chats. Now with PostgreSQL database integration for scalability and reliability.

## ✨ Features

### 🔗 **Link Processing**
- **Universal Terabox Support**: Accepts links from multiple Terabox domains
- **Smart URL Normalization**: Automatically converts alternative domains to terabox.com for API compatibility
- **Intelligent Link Detection**: Automatically processes Terabox links in messages (no commands needed in private chats)
- **Multiple Link Support**: Process multiple Terabox links in a single message

### 💬 **Chat Integration**
- **Dual Chat Support**: Works seamlessly in both private chats and groups
- **Smart Group Behavior**: Only responds when explicitly mentioned or using commands
- **User Authentication**: Secure authentication system with personal auth keys
- **Admin Controls**: Special admin-only features for group management

### 🗄️ **Database & Scalability**
- **PostgreSQL Integration**: Enterprise-grade database storage via Neon.tech
- **Duplicate Detection**: Smart caching prevents re-downloading the same files
- **User Management**: Persistent user authentication across bot restarts
- **Download History**: Complete download cache with automatic cleanup
- **Multi-Instance Support**: Multiple bot instances can share the same database

### ⚡ **Performance & Reliability**
- **Asynchronous Processing**: Non-blocking download monitoring with queue system
- **Concurrent Downloads**: Support for multiple simultaneous downloads (configurable limit)
- **Rate Limiting**: Built-in API protection with intelligent throttling
- **Graceful Shutdown**: Professional Ctrl+C handling with clean resource cleanup
- **Auto-Recovery**: Robust error handling with automatic retries

### 📊 **Monitoring & Status**
- **Real-time Progress**: Live status updates during processing with progress bars
- **Download Queue**: View active and queued downloads with position tracking
- **Statistics**: Database statistics and download metrics
- **Comprehensive Logging**: Detailed logs with UTF-8 support and rotation

### 🎥 **File Handling**
- **Intelligent Upload**: Detects video files for optimal Telegram delivery
- **Large File Support**: Up to 2GB files with local Bot API server
- **Smart File Types**: Automatic video/document detection and appropriate upload
- **Temporary File Management**: Automatic cleanup with configurable temp directories

### 🛡️ **Security & Admin Features**
- **Nuclear Option**: `/nuke` command to delete all messages in a chat (with confirmation)
- **Admin Verification**: Group admin checks for destructive operations
- **Secure Authentication**: Environment-based auth key system
- **Permission Controls**: Different behavior for private vs group chats

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Torbox API token (from [Torbox.app](https://torbox.app))
- A Neon.tech PostgreSQL database (free tier available)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd torboxTG
   ```

2. **Install dependencies**:
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

3. **Set up Neon.tech Database:**
   - Go to [Neon.tech](https://neon.tech) and create a free account
   - Create a new database project
   - Copy your PostgreSQL connection string from the dashboard
   - It should look like: `postgresql://username:password@hostname/database?sslmode=require`

4. **Configure environment variables**:
   ```bash
   cp config.env.template .env
   ```
   
   Edit the `.env` file with your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TORBOX_API_TOKEN=your_torbox_api_token_here
   AUTH_KEY=your_secret_auth_key_here
   DATABASE_URL=postgresql://username:password@hostname/database?sslmode=require
   ```

5. **Initialize the database**:
   ```bash
   python setup_db.py setup
   ```

6. **Start the bot**:
   ```bash
   # Using the enhanced runner (recommended)
   python run.py
   
   # Or directly
   python main.py
   ```

## 🔗 Supported Terabox Domains

The bot accepts links from **multiple Terabox domains** but automatically normalizes them to `terabox.com` for Torbox API compatibility:

- `terabox.com` (primary domain)
- `1024terabox.com` → normalized to `terabox.com`
- `teraboxapp.com` → normalized to `terabox.com`
- `nephobox.com` → normalized to `terabox.com` 
- `4funbox.com` → normalized to `terabox.com`
- `mirrobox.com` → normalized to `terabox.com`
- `momerybox.com` → normalized to `terabox.com`
- `teraboxlink.com` → normalized to `terabox.com`
- `terasharelink.com` → normalized to `terabox.com`

**Why normalization?** Torbox API only supports the main `terabox.com` domain, so the bot automatically converts alternative domains for API compatibility.

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather |
| `TORBOX_API_TOKEN` | Your Torbox API token |
| `AUTH_KEY` | Secret key for bot authentication |
| `DATABASE_URL` | PostgreSQL connection string from Neon.tech |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_API_URL` | Empty | Local Bot API server URL (for bypassing 50MB limit) |
| `MAX_FILE_SIZE` | `2147483648` (2GB) | Maximum file size in bytes |
| `DOWNLOAD_TIMEOUT` | `3600` (1 hour) | Download timeout in seconds |
| `UPLOAD_TIMEOUT` | `1800` (30 min) | Upload timeout in seconds |
| `TEMP_DIR` | System temp | Temporary directory for downloads |

## 🔧 Local Bot API Server (Optional)

To bypass Telegram's 50MB file upload limit and enable 2GB uploads:

### Setup Local Bot API Server

1. **Download Telegram Bot API Server**:
   ```bash
   # For Linux/macOS
   wget https://github.com/tdlib/telegram-bot-api/releases/latest/download/telegram-bot-api-linux
   chmod +x telegram-bot-api-linux
   
   # For Windows, download the .exe from the releases page
   ```

2. **Run the Bot API Server**:
   ```bash
   # Basic setup (HTTP on port 8081)
   ./telegram-bot-api-linux --api-id=YOUR_API_ID --api-hash=YOUR_API_HASH --local
   
   # With custom port
   ./telegram-bot-api-linux --api-id=YOUR_API_ID --api-hash=YOUR_API_HASH --local --http-port=8081
   ```

3. **Configure TorboxTG**:
   ```bash
   # In your .env file
   TELEGRAM_API_URL=http://localhost:8081
   ```

### Benefits of Local Bot API Server
- **No 50MB limit**: Upload files up to 2GB
- **Faster uploads**: Direct server communication
- **Better reliability**: No third-party API rate limits

## 📱 Usage

### Starting the Bot

```bash
# Enhanced startup with validation (recommended)
python run.py

# Direct startup
python main.py
```

The enhanced runner (`run.py`) provides:
- ✅ Dependency checking
- ✅ Environment validation
- ✅ Database connectivity testing
- ✅ Comprehensive error reporting

### Bot Commands

| Command | Description | Availability |
|---------|-------------|--------------|
| `/start` | Show welcome message and usage instructions | All users |
| `/help` | Display help information and supported features | All users |
| `/auth <key>` | Authenticate with the bot using your auth key | All users |
| `/status` | Check your active and queued downloads | Authenticated users |
| `/tb <link>` | Process a Terabox link (groups only) | Authenticated users |
| `/nuke` | ⚠️ Delete all messages in chat (DANGEROUS!) | Authenticated users/Admins |

### Authentication

Before using the bot, you must authenticate:

```
/auth your_secret_auth_key_here
```

The auth key is set in your `.env` file as `AUTH_KEY`.

### Usage Examples

#### Private Chat
```
# Authenticate first
/auth your_secret_key

# Then simply send Terabox links (no command needed)
https://terabox.com/s/1234567890abcdef

# Or send multiple links at once
Check these files:
https://terabox.com/s/1234567890abcdef
https://1024terabox.com/s/abcdef1234567890
```

#### Group Chat
```
# Authenticate first
/auth your_secret_key

# Use the /tb command
/tb https://terabox.com/s/1234567890abcdef

# Or mention the bot
@YourBotName https://terabox.com/s/1234567890abcdef
```

#### Nuclear Option (Use with EXTREME caution!)
```
# In private chat or as group admin
/nuke

# Bot will show a warning with confirmation buttons
# Click "💥 I REALLY WANT TO DO THIS" to proceed
# This will DELETE ALL MESSAGES the bot can access!
```

## 🔄 How It Works

1. **Authentication**: Users authenticate with a shared secret key
2. **Link Detection**: Bot automatically detects Terabox links in messages
3. **Duplicate Check**: Database is checked for previously processed links
4. **Queue Management**: Downloads are queued if concurrent limit is reached
5. **Torbox Integration**: Links are sent to Torbox via their web download API
6. **Progress Monitoring**: Bot checks download status with real-time updates
7. **File Download**: Once ready, files are downloaded to temporary storage
8. **Smart Upload**: Files are uploaded as videos or documents based on type
9. **Database Storage**: Completed downloads are cached for future duplicate detection
10. **Cleanup**: Temporary files and old database entries are automatically cleaned

## 🗄️ Database Management

### Database Commands

```bash
# Initialize database tables
python setup_db.py setup

# View database statistics
python setup_db.py stats

# Clean up old downloads (keeps 5000 most recent)
python setup_db.py cleanup

# Show help
python setup_db.py help
```

### Database Features

- **Automatic table creation** on first run
- **Duplicate detection** prevents re-downloading same files
- **User authentication** persistence across restarts
- **Download history** with automatic cleanup
- **Connection pooling** for performance
- **SSL support** for secure connections

## 📊 Monitoring & Logging

### Log Files

- `torboxtg.log` - Main application logs with rotation
- Console output with colored status indicators
- UTF-8 encoding support for international characters

### Status Monitoring

```bash
# Check download status
/status

# View database statistics
python setup_db.py stats
```

### Progress Indicators

The bot provides real-time progress updates:
- 🔄 Processing link
- ⏳ Queued (position shown)
- 📥 Downloading with progress bar
- 📤 Uploading to Telegram
- ✅ Complete with file info

## 🛡️ Security Features

### Authentication System
- Environment-based auth keys
- Per-user authentication tracking
- Database persistence

### Admin Controls
- Group admin verification for destructive commands
- Permission-based feature access
- Secure callback handling

### Nuclear Option Safety
- Multiple confirmation steps
- Admin-only in groups
- Detailed warning messages
- Security checks and logging

## 🔧 Advanced Configuration

### Queue Management

```python
# In main.py, adjust these settings:
self.max_concurrent_downloads = 2  # Concurrent download limit
```

### Rate Limiting

```python
# Throttler configuration
throttler = Throttler(rate_limit=5, period=60)  # 5 requests per minute
```

### Database Cleanup

```python
# Automatic cleanup keeps 5000 most recent downloads
await bot.cleanup_old_downloads()
```

## 🚀 Deployment

### Production Deployment

1. **Use environment variables** for all configuration
2. **Set up database** with proper SSL certificates
3. **Configure logging** with appropriate levels
4. **Monitor resources** (CPU, memory, disk space)
5. **Set up process management** (systemd, pm2, etc.)

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["python", "run.py"]
```

### Systemd Service Example

```ini
[Unit]
Description=TorboxTG Bot
After=network.target

[Service]
Type=simple
User=torboxbot
WorkingDirectory=/path/to/torboxTG
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🛠️ Development

### Project Structure

```
torboxTG/
├── main.py                 # Main bot implementation
├── database.py             # Database management and models
├── run.py                  # Enhanced startup runner with validation
├── setup_db.py             # Database setup and management tools
├── pyproject.toml          # Project dependencies and configuration
├── requirements.txt        # Python dependencies
├── config.env.template     # Environment variables template
├── README.md              # This documentation
├── INSTALL.md             # Installation instructions
└── torboxtg.log           # Log file (created at runtime)
```

### Key Classes

- `TorboxAPI`: Handles all Torbox API interactions
- `TorboxTelegramBot`: Main bot logic and Telegram integration
- `DatabaseManager`: Database operations and connection management
- `CompletedDownload`: Database model for download cache
- `AuthenticatedUser`: Database model for user authentication

### API Endpoints Used

The bot uses the following Torbox API endpoints:
- `POST /webdl/createwebdownload` - Create web download
- `GET /webdl/mylist` - Get download list and status
- `GET /webdl/requestdl` - Request download link

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**:
   ```bash
   # Check your DATABASE_URL format
   # Ensure Neon.tech database is running
   # Verify SSL requirements
   python setup_db.py setup
   ```

2. **Bot Not Responding**:
   - Verify `TELEGRAM_BOT_TOKEN` is correct
   - Check if bot is added to the chat
   - Ensure users are authenticated with `/auth`

3. **Authentication Failed**:
   - Verify `AUTH_KEY` in environment
   - Check user used correct auth key
   - Review authentication logs

4. **Download Failures**:
   - Ensure Terabox link is public and accessible
   - Check Torbox API quota and limits
   - Verify network connectivity

5. **Upload Failures**:
   - Check file size limits (50MB without local API)
   - Verify bot permissions in chat
   - Monitor disk space in temp directory

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python main.py
```

### Health Checks

```bash
# Test database connection
python -c "from database import init_database; import asyncio; asyncio.run(init_database('your_db_url'))"

# Validate environment
python run.py --check-only  # If implemented

# Test bot token
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

## 📈 Performance Optimization

### Database Optimization
- Connection pooling enabled by default
- Automatic cleanup of old downloads
- Indexed queries for fast duplicate detection
- SSL connections for security

### Memory Management
- Temporary file cleanup after uploads
- Streaming downloads for large files
- Async operations prevent blocking

### Network Optimization
- Rate limiting prevents API abuse
- Connection reuse for HTTP requests
- Timeout handling for reliability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/torboxTG.git
cd torboxTG

# Install in development mode
pip install -e ".[dev]"

# Set up pre-commit hooks (if available)
pre-commit install
```

## 📄 License

This project is open source. Please check the license file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use. Users are responsible for:
- Complying with Terabox's terms of service
- Only downloading content they have permission to access
- Respecting copyright and intellectual property rights
- Following local laws and regulations

## 🆘 Support

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Review the logs** for error details (`torboxtg.log`)
3. **Test your configuration** using the validation tools
4. **Create an issue** with:
   - Detailed problem description
   - Log excerpts (remove sensitive data)
   - Environment details (OS, Python version)
   - Steps to reproduce

## 🙏 Acknowledgments

- [Torbox.app](https://torbox.app) for the debrid API
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the Telegram integration
- [Neon.tech](https://neon.tech) for PostgreSQL hosting
- The open-source community for inspiration and tools

---

**Made with ❤️ for the community**
