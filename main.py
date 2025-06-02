import os
import logging
import asyncio
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
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with enhanced media processing"""
    message = update.effective_message
    user = message.from_user
    
    # Skip if no processable media
    if not (message.photo or message.sticker):
        return
    
    media_files = []
    try:
        # Process media (returns list of image paths)
        media_files = await process_media(message, context.bot)
        if not media_files:
            logger.warning("Media processing failed or returned no files")
            return
        
        # Classify content
        content_result = await classify_content(media_files)
        
        # Apply content policy
        if policy.should_delete(content_result):
            try:
                await message.delete()
                logger.warning(
                    f"🚫 Deleted prohibited content from {user.full_name} ({user.id}): "
                    f"Type: {content_result.get('content_type', 'unknown')}, "
                    f"Scores: N={content_result.get('max_explicit', 0):.2f}, "
                    f"CA={content_result.get('max_child_abuse', 0):.2f}, "
                    f"V={content_result.get('max_violence', 0):.2f}"
                )
                
                # Send warning to user
                try:
                    warning = await message.reply_text(
                        "⚠️ Your content was removed for violating community guidelines. "
                        "Repeated violations will result in a ban."
                    )
                    # Auto-remove warning after 10 seconds
                    await asyncio.sleep(10)
                    await warning.delete()
                except Exception as e:
                    logger.error(f"Failed to send warning: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
        else:
            logger.info(f"✅ Content approved: {user.full_name} ({user.id})")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
    finally:
        # Cleanup temporary files
        for file_path in media_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Failed to clean up {file_path}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🛡️ Advanced Auto-Moderation Bot is active!\n\n"
        "I automatically detect and remove:\n"
        "• Expliciiit 18+ content\n"
        "• Child exploitation material\n"
        "• Violent/graphic content\n"
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
               f"Explicit threshold={policy.explicit_threshold}, "
               f"Child abuse threshold={policy.child_abuse_threshold}")
    
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
