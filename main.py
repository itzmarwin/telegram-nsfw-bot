import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)
from media_processor import process_media
from nudenet_wrapper import classify_nsfw

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
NSFW_THRESHOLD = 0.7  # 70% probability threshold

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and process media"""
    message = update.effective_message
    user = message.from_user
    
    # Skip if message doesn't contain processable media
    if not (message.photo or message.sticker):
        return
    
    try:
        # Determine media type and process
        media_file = await process_media(message, context.bot)
        if not media_file:
            return
            
        # Classify NSFW content
        nsfw_score = await classify_nsfw(media_file)
        logger.info(f"NSFW scan result for {user.id}: {nsfw_score:.2f}")
        
        # Delete if NSFW detected
        if nsfw_score >= NSFW_THRESHOLD:
            await message.delete()
            logger.info(f"Deleted NSFW content from {user.id} (Score: {nsfw_score:.2f})")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        # Cleanup temporary files
        if media_file and os.path.exists(media_file):
            os.remove(media_file)

async def post_init(application: Application):
    """Post initialization message"""
    await application.bot.set_my_commands([('start', 'Initialize the bot')])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🛡️ NSFW Auto-Moderation Bot is active!\n\n"
        "I automatically detect and delete:\n"
        "• Explicit images\n"
        "• NSFW stickers\n"
        "• Adult video stickers\n\n"
        "Normal content is never deleted. Make me admin with delete permissions!"
    )

def main():
    """Start the bot"""
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Sticker.ALL,
        handle_message
    ))
    app.add_handler(CommandHandler("start", start))
    
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
