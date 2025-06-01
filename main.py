import os
import logging
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from media_processor import process_media
from nudenet_wrapper import classify_content
from content_policy import policy

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    
    # Skip if no processable media (photos or stickers)
    if not (message.photo or message.sticker):
        return
    
    media_file = None
    try:
        # Process media (convert stickers to images)
        media_file = await process_media(message, context.bot)
        if not media_file:
            return
            
        # Classify content using NudeNet
        content_result = await classify_content(media_file)
        
        # Log results
        logger.info(
            f"Content scan for user {user.id}: "
            f"Nudity: {content_result['nudity']:.2f}, "
            f"Child Abuse: {content_result['child_abuse']}, "
            f"Violence: {content_result['violence']}"
        )
        
        # Apply content policy
        if policy.should_delete(content_result):
            await message.delete()
            logger.warning(
                f"Deleted prohibited content from user {user.id}: "
                f"Type: {content_result['content_type']}"
            )
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        # Cleanup temporary files
        if media_file and os.path.exists(media_file):
            os.remove(media_file)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🛡️ Auto-Moderation Bot is active!\n\n"
        "I automatically detect and delete:\n"
        "• Explicit 18+ content\n"
        "• Child abuse material\n"
        "• Violent content\n\n"
        "Normal stickers and images are never deleted!"
    )

def main():
    """Start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()
    
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
