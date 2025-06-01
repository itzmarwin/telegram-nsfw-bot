# Telegram Content Moderation Bot

Automatically detects and deletes prohibited content in Telegram groups:

## Features
- 🚫 Deletes 18+ explicit content
- 🛡️ Blocks child abuse material
- 🔫 Removes violent content
- 🖼️ Processes images and static stickers
- 📹 Handles video stickers and animated stickers
- ⚙️ Configurable sensitivity thresholds
- 📊 Detailed logging for moderation actions

## System Requirements
- Docker
- FFmpeg
- Python 3.11+
- Cairo graphics library

## Installation

### Docker Setup (Recommended)
```bash
# Build the image
docker build -t telegram-mod-bot .

# Run the container
docker run -d \
  --name mod-bot \
  -e BOT_TOKEN="YOUR_BOT_TOKEN" \
  -e NUDITY_THRESHOLD=0.75 \
  telegram-mod-bot
