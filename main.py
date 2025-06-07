import os
import logging
import asyncio
import time
import shutil

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from media_processor import process_media
from nudenet_wrapper import classify_content
from content_policy import policy
from database import db
from commands import (
    start_command,
    stats_command,
    broadcast_command,
    addsudo_command,
    rmsudo_command,
    sudolist_command,
    callback_handler
)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)

def is_ffmpeg_available():
    """Check if FFmpeg is installed"""
    return shutil.which("ffmpeg") is not None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages with performance optimizations"""
    start_time = time.time()
    message = update.effective_message
    user = message.from_user
    chat = update.effective_chat

    # Track group in database
    if chat.type in ["group", "supergroup"]:
        if db.is_connected():
            db.add_group(
                chat_id=chat.id,
                title=chat.title
            )

    # Skip if no processable media
    if not (message.photo or message.sticker):
        return

    media_files = []
    try:
        # Process media with timeout
        try:
            media_files = await asyncio.wait_for(
                process_media(message, context.bot),
                timeout=15
            )
        except asyncio.TimeoutError:
            logger.warning("Media processing timed out")
            return

        if not media_files:
            logger.debug("Media processing returned no files")
            return

        # Classify content with timeout
        try:
            content_result = await asyncio.wait_for(
                classify_content(media_files),
                timeout=20
            )
        except asyncio.TimeoutError:
            logger.warning("Classification timed out")
            return

        # Apply content policy
        if policy.should_delete(content_result):
            try:
                await message.delete()
                logger.warning(
                    f"🚫 Deleted prohibited content from {user.full_name} ({user.id}) in chat {chat.id}: "
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
            logger.info(f"✅ Content approved from {user.full_name} ({user.id}) in chat {chat.id}")

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

        # Log performance
        proc_time = time.time() - start_time
        logger.info(f"⏱️ Processing time: {proc_time:.2f}s")
        if proc_time > 5.0:
            logger.warning(f"Slow processing detected: {proc_time:.2f}s")

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added to a group"""
    new_members = update.message.new_chat_members
    bot_id = context.bot.id
    
    # Check if bot was added
    if any(member.id == bot_id for member in new_members):
        chat = update.effective_chat
        logger.info(f"🤖 Bot added to group: {chat.title} ({chat.id})")
        
        if db.is_connected():
            db.add_group(
                chat_id=chat.id,
                title=chat.title
            )

def main():
    """Start the bot"""
    # Verify environment
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    if OWNER_ID == 0:
        logger.warning("OWNER_ID not set! Sudo features will be disabled")

    app = Application.builder().token(BOT_TOKEN).build()

    # Check FFmpeg availability
    if not is_ffmpeg_available():
        logger.warning("⚠️ FFmpeg not installed! Video processing disabled.")
    else:
        logger.info("✅ FFmpeg available for video processing")
    
    # Check database connection
    if db.is_connected():
        logger.info("✅ MongoDB connection established")
    else:
        logger.warning("⚠️ MongoDB connection failed! Some features disabled")

    # Add handlers
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("addsudo", addsudo_command))
    app.add_handler(CommandHandler("rmsudo", rmsudo_command))
    app.add_handler(CommandHandler("sudolist", sudolist_command))
    
    # Button callback handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handler for media
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Sticker.ALL,
        handle_message
    ))
    
    # Handler for bot being added to groups
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))

    logger.info("🤖 Bot is starting...")
    logger.info(f"🔍 Using policy: "
                f"Explicit threshold={policy.explicit_threshold}, "
                f"Partial nudity threshold={policy.partial_nudity_threshold}")
    logger.info(f"👑 Owner ID: {OWNER_ID}")

    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
