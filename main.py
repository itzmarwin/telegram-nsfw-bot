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

# Configure logging based on environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and process media with enhanced detection"""
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
            logger.warning("Media processing failed")
            return
            
        # Classify content using NudeNet
        content_result = await classify_content(media_file)
        
        # Log detailed results
        logger.debug(f"Full detection results: {content_result}")
        
        # Apply content policy
        if policy.should_delete(content_result):
            try:
                await message.delete()
                logger.warning(
                    f"🚫 Deleted prohibited content from {user.full_name} ({user.id}): "
                    f"Type: {content_result['content_type']}, "
                    f"Objects: {list(content_result['detected_objects'].keys())}"
                )
                
                # Send warning to user
                try:
                    await message.reply_text(
                        "⚠️ Your content was deleted because it violates our community guidelines. "
                        "Repeated violations may result in a ban."
                    )
                except Exception as e:
                    logger.error(f"Failed to send warning: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
        else:
            logger.info("✅ Content is safe, no action taken")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
    finally:
        # Cleanup temporary files
        if media_file and os.path.exists(media_file):
            try:
                os.remove(media_file)
                logger.debug(f"Cleaned up temporary file: {media_file}")
            except Exception as e:
                logger.error(f"Failed to clean up {media_file}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🛡️ Auto-Moderation Bot is active!\n\n"
        "I automatically detect and delete:\n"
        "• Explicit 18+ content\n"
        "• Child abuse material\n"
        "• Violent content\n"
        "• Drug-related material\n\n"
        "Normal stickers and images are never deleted!"
    )

def main():
    """Start the bot"""
    # Verify environment
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Sticker.ALL,
        handle_message
    ))
    app.add_handler(CommandHandler("start", start))
    
    logger.info("🤖 Bot is starting...")
    logger.info(f"🔍 Using policy: "
               f"Nudity threshold={policy.nudity_threshold}, "
               f"Child abuse threshold={policy.child_abuse_threshold}, "
               f"Violence threshold={policy.violence_threshold}")
    
    try:
        app.run_polling()
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
