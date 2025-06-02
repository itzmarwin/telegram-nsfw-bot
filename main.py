import os
import logging
import asyncio
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from media_processor import process_media
from nudenet_wrapper import classify_content
from content_policy import policy

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=log_level
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = message.from_user
    
    # Skip admins
    if user.id in ADMIN_IDS:
        return
    
    # Skip non-media
    if not (message.photo or message.sticker):
        return
    
    media_paths = []
    try:
        # Process media (returns multiple enhanced versions)
        media_paths = await process_media(message, context.bot)
        if not media_paths:
            return
        
        # Classify all versions
        result = await classify_content(media_paths)
        
        # Apply aggressive policy
        if policy.should_delete(result):
            try:
                await message.delete()
                logger.warning(
                    f"Deleted content from {user.full_name} ({user.id}): "
                    f"Explicit={result['max_explicit']:.2f}, "
                    f"Suggestive={result['max_suggestive']:.2f}, "
                    f"Child={result['max_child_abuse']:.2f}"
                )
                
                # Notify user
                try:
                    warn = await message.reply_text(
                        "⚠️ Your content was removed for violating community standards. "
                        "Repeated violations will result in a ban."
                    )
                    await asyncio.sleep(10)
                    await warn.delete()
                except:
                    pass
            except Exception as e:
                logger.error(f"Delete failed: {e}")
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
    finally:
        # Cleanup
        for path in media_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ Advanced NSFW Detection Bot\n\n"
        "I automatically detect and remove:\n"
        "- Explicit content\n"
        "- Suggestive material\n"
        "- Child exploitation\n"
        "- Violent content\n\n"
        "Using advanced AI detection algorithms"
    )

def main():
    if not BOT_TOKEN:
        logger.error("Missing BOT_TOKEN")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO | filters.Sticker.ALL, handle_message))
    app.add_handler(CommandHandler("start", start))
    
    logger.info("Starting enhanced NSFW detection bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
