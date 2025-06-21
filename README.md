## 🤖 TorboxTG Bot

A powerful Telegram bot that debrids Terabox links using the Torbox API and delivers files directly to your Telegram chats.

## ✨ Features

- **🔗 Universal Terabox Support**: Accepts links from multiple Terabox domains
- **🔄 Smart URL Normalization**: Automatically converts alternative domains to terabox.com for API compatibility
- **💬 Dual Chat Support**: Works seamlessly in both private chats and groups
- **📱 Smart Group Behavior**: Only responds when explicitly called in groups
- **⚡ Asynchronous Processing**: Non-blocking download monitoring
- **📊 Real-time Progress**: Live status updates during processing
- **🎥 Intelligent Upload**: Detects video files for optimal Telegram delivery
- **👤 User Tracking**: Personal download history and status
- **🛡️ Rate Limiting**: Built-in API protection
- **🗂️ File Management**: Automatic temporary file cleanup

## 📋 Bot Setup

### No Separate Group Token Needed!

**Important**: You only need **ONE** Telegram bot token that works for:
- ✅ Private chats (direct messages)
- ✅ Group chats 
- ✅ Supergroups
- ✅ Channels

The bot just needs to be **added to groups by an admin** - no separate tokens required!

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

## Prerequisites

- Python 3.9 or higher
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Torbox API token (from [Torbox.app](https://torbox.app))

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd torboxTG
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Configure environment variables**:
   ```bash
   cp config.env.template .env
   ```
   
   Edit the `.env` file with your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TORBOX_API_TOKEN=your_torbox_api_token_here
   ```

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather |
| `TORBOX_API_TOKEN` | Your Torbox API token |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_API_URL` | Empty (optional) | Local Bot API server URL (for bypassing 50MB limit) |
| `MAX_FILE_SIZE` | `2147483648` (2GB) | Maximum file size in bytes |
| `DOWNLOAD_TIMEOUT` | `3600` (1 hour) | Download timeout in seconds |
| `TEMP_DIR` | System temp | Temporary directory for downloads |

## Local Bot API Server (Optional)

To bypass Telegram's 50MB file upload limit, you can set up a local Bot API server:

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

## Usage

### Starting the Bot

```bash
python main.py
```

### Bot Commands

- `/start` - Show welcome message and usage instructions
- `/help` - Display help information and supported features
- `/tb <terabox_link>` - Process a Terabox link
- `/status` - Check your active downloads

### Example Usage

1. **Basic usage**:
   ```
   /tb https://terabox.com/s/1234567890abcdef
   ```

2. **The bot will**:
   - Validate the Terabox link
   - Send it to Torbox for processing
   - Monitor the download progress
   - Download the file when ready
   - Upload it to Telegram automatically

## How It Works

1. **Link Processing**: When you send a `/tb` command with a Terabox link, the bot validates the URL
2. **Torbox Integration**: The link is sent to Torbox via their web download API
3. **Progress Monitoring**: The bot checks the download status every minute
4. **File Download**: Once ready, the bot downloads the file to a temporary location
5. **Telegram Upload**: The file is uploaded to Telegram (as video if it's a video file)
6. **Cleanup**: Temporary files are automatically cleaned up

## API Endpoints Used

The bot uses the following Torbox API endpoints:
- `POST /webdl/createwebdl` - Create web download
- `GET /webdl/getwebdlinfo` - Get download information
- `POST /webdl/requestdl` - Request download link

## Logging

The bot creates a `torboxtg.log` file with detailed logging information. Logs include:
- API requests and responses
- Download progress
- Error messages
- File processing status

## Error Handling

The bot handles various error scenarios:
- Invalid Terabox links
- API rate limits
- Download failures
- File size exceeding limits
- Network timeouts
- Telegram upload errors

## Rate Limiting

The bot implements rate limiting to respect Torbox API limits:
- Maximum 10 requests per minute to Torbox API
- Automatic retry with exponential backoff on rate limit errors

## Development

### Project Structure

```
torboxTG/
├── main.py                 # Main bot implementation
├── pyproject.toml         # Project dependencies and configuration
├── README.md              # This file
├── config.env.template    # Environment variables template
└── torboxtg.log          # Log file (created at runtime)
```

### Key Classes

- `TorboxAPI`: Handles all Torbox API interactions
- `TorboxTelegramBot`: Main bot logic and Telegram integration

### Adding New Features

To add new features:
1. Implement new methods in the `TorboxTelegramBot` class
2. Add command handlers in the `create_application` method
3. Update the help text and README

## Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check if `TELEGRAM_BOT_TOKEN` is correct
   - Verify bot is added to the chat
   - Check logs for errors

2. **Torbox API errors**:
   - Verify `TORBOX_API_TOKEN` is valid
   - Check if you have remaining quota
   - Review rate limiting errors in logs

3. **Download failures**:
   - Ensure Terabox link is public and accessible
   - Check if file size exceeds limits
   - Verify network connectivity

4. **Upload failures**:
   - Check if file size exceeds Telegram limits
   - Verify bot has permission to send files
   - Review temporary disk space

### Debug Mode

To enable debug logging, modify the logging level in `main.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    # ... rest of config
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Disclaimer

This bot is for educational purposes. Ensure you comply with Terabox's terms of service and only download content you have permission to access.

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue with detailed information about the problem
