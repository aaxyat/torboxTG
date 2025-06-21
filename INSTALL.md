# Installation Guide for TorboxTG Bot

This guide will walk you through setting up the TorboxTG bot step by step.

## Prerequisites

### 1. Python Installation
- **Windows**: Download from [python.org](https://python.org) (Python 3.9+)
- **Linux/macOS**: Usually pre-installed, or install via package manager
- **Check version**: `python --version` or `python3 --version`

### 2. Get Telegram Bot Token
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Save the token (format: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 3. Get Torbox API Token
1. Visit [Torbox.app](https://torbox.app)
2. Create an account or sign in
3. Go to your account settings/API section
4. Generate or copy your API token

## Installation Steps

### Step 1: Download the Project
```bash
# Clone from Git (if available)
git clone <repository_url>
cd torboxTG

# OR download and extract ZIP file, then navigate to folder
cd torboxTG
```

### Step 2: Install Dependencies

#### Option A: Using pip (recommended)
```bash
pip install -r requirements.txt
```

#### Option B: Using pyproject.toml
```bash
pip install -e .
```

#### Option C: Manual installation
```bash
pip install python-telegram-bot>=20.7
pip install aiohttp>=3.9.0
pip install aiofiles>=23.0.0
pip install python-dotenv>=1.0.0
pip install pydantic>=2.0.0
pip install asyncio-throttle>=1.0.0
```

### Step 3: Configure Environment

#### Create configuration file:
```bash
# Copy template
cp config.env.template .env

# Edit the file with your tokens
```

#### Edit .env file:
Open `.env` in a text editor and add your tokens:
```env
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TORBOX_API_TOKEN=your_torbox_api_token_here

# Optional settings (use defaults if unsure)
MAX_FILE_SIZE=2147483648
DOWNLOAD_TIMEOUT=3600
TEMP_DIR=/tmp
```

### Step 4: Test the Setup

#### Using the startup script (recommended):
```bash
python run.py
```

#### Or run directly:
```bash
python main.py
```

## Verification

### 1. Check Bot Status
If everything is working, you should see:
```
🤖 TorboxTG Bot starting...
📁 Temp directory: /tmp
📊 Max file size: 2.0 GB
INFO - Application started
```

### 2. Test in Telegram
1. Find your bot in Telegram (use the username from BotFather)
2. Send `/start` command
3. You should receive a welcome message

### 3. Test with a Terabox Link
1. Send: `/tb https://terabox.com/s/your_test_link`
2. The bot should acknowledge and start processing

## Troubleshooting

### Common Issues

#### 1. "No module named 'telegram'"
```bash
# Install missing dependencies
pip install -r requirements.txt
```

#### 2. "TELEGRAM_BOT_TOKEN not found"
- Check if `.env` file exists in the project folder
- Verify the token format is correct
- Make sure there are no extra spaces in the .env file

#### 3. "API Error: 401"
- Check your Torbox API token
- Verify you have an active Torbox subscription
- Ensure the token has necessary permissions

#### 4. Bot doesn't respond in Telegram
- Check if the bot token is correct
- Verify the bot is not blocked
- Check firewall/network settings
- Look at the console logs for errors

#### 5. "Permission denied" errors
- Check file permissions: `chmod +x run.py`
- Ensure you have write access to the temp directory
- Try running with different temp directory

### Debug Mode

Enable detailed logging:
1. Open `main.py`
2. Find the logging configuration
3. Change `level=logging.INFO` to `level=logging.DEBUG`
4. Restart the bot

### Getting Help

If you encounter issues:

1. **Check logs**: Look at `torboxtg.log` for detailed error messages
2. **Verify setup**: Run `python run.py` for environment validation
3. **Test components**:
   ```bash
   # Test Python packages
   python -c "import telegram; print('Telegram OK')"
   python -c "import aiohttp; print('aiohttp OK')"
   ```

### Performance Tips

1. **Large files**: Increase `DOWNLOAD_TIMEOUT` for large files
2. **Storage**: Ensure sufficient disk space in temp directory
3. **Network**: Stable internet connection recommended
4. **Torbox quota**: Monitor your Torbox usage limits

## Security Notes

1. **Keep tokens private**: Never share your `.env` file
2. **File permissions**: Set restrictive permissions on `.env`
   ```bash
   chmod 600 .env
   ```
3. **Bot usage**: Only use with content you have permission to download
4. **Updates**: Keep dependencies updated for security

## Next Steps

Once installed:
1. Read the main [README.md](README.md) for usage instructions
2. Check supported Terabox domains
3. Learn about bot commands and features
4. Consider setting up as a system service for 24/7 operation

## System Service Setup (Optional)

### Linux (systemd)
Create a service file `/etc/systemd/system/torboxtg.service`:
```ini
[Unit]
Description=TorboxTG Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/torboxTG
ExecStart=/usr/bin/python3 /path/to/torboxTG/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable torboxtg
sudo systemctl start torboxtg
```

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task
3. Set to run at startup
4. Action: Start a program
5. Program: `python`
6. Arguments: `/path/to/torboxTG/main.py`
7. Start in: `/path/to/torboxTG/`

## Support

For additional help:
- Check the [README.md](README.md) for detailed documentation
- Review the troubleshooting section above
- Check the logs in `torboxtg.log`
- Create an issue with detailed error information 