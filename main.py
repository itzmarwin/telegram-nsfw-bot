import os
import logging
import asyncio
import time
from dotenv import load_dotenv
load_dotenv()
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from content_policy import policy
from sticker_manager import StickerManager

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "nsfw_bot")

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)

# Initialize sticker manager
sticker_manager = StickerManager(MONGO_URI, DB_NAME)

async def detect_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /detectsticker command"""
    user = update.effective_user
    message = update.effective_message
    
    # Check if user is admin
    if user.id not in ADMIN_IDS:
        await message.reply_text("🚫 This command is only available to admins.")
        return
    
    # Check if message is a reply to a sticker
    if not message.reply_to_message or not message.reply_to_message.sticker:
        await message.reply_text("ℹ️ Please reply to a sticker with /detectsticker to analyze it.")
        return
    
    sticker_msg = message.reply_to_message
    sticker = sticker_msg.sticker
    
    # Send processing message
    processing_msg = await message.reply_text("🔍 Analyzing sticker...")
    
    # Analyze sticker
    result_text, feature_vector = await sticker_manager.analyze_sticker(sticker_msg, context.bot)
    
    if not result_text:
        await processing_msg.edit_text(feature_vector)  # feature_vector contains error message
        return
    
    # Store results in database
    sticker_manager.store_sticker_analysis(sticker, feature_vector, user.id)
    
    # Create action buttons
    reply_markup = sticker_manager.create_action_buttons(sticker.file_unique_id)
    
    await processing_msg.edit_text(result_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks from sticker analysis"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Check if user is admin
    if user.id not in ADMIN_IDS:
        await query.edit_message_text("🚫 This action is only available to admins.")
        return
    
    # Handle different actions
    if data.startswith("add_nsfw_"):
        file_unique_id = data.split("_")[2]
        if sticker_manager.add_to_nsfw(file_unique_id, user.id):
            await query.edit_message_text("✅ Sticker added to NSFW database.")
        else:
            await query.edit_message_text("❌ Failed to add sticker to NSFW database.")
        
    elif data == "cancel_action":
        await query.edit_message_text("❌ Action canceled.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    start_time = time.time()
    message = update.effective_message
    user = message.from_user
    
    # Skip if no processable media
    if not (message.photo or message.sticker):
        return
    
    # Check if sticker is in NSFW database
    if message.sticker:
        sticker = message.sticker
        if sticker_manager.is_nsfw_sticker(sticker.file_unique_id):
            try:
                await message.delete()
                logger.warning(f"🚫 Deleted NSFW sticker from {user.full_name} ({user.id})")
                
                # Send warning to user
                try:
                    warning = await message.reply_text(
                        "⚠️ Your sticker was removed for violating NSFW policy."
                    )
                    await asyncio.sleep(10)
                    await warning.delete()
                except Exception as e:
                    logger.error(f"Failed to send warning: {e}")
                
                return
            except Exception as e:
                logger.error(f"Failed to delete NSFW sticker: {e}")
    
    # Process media (existing code remains the same)
    # ... [Keep your existing media processing logic here] ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🛡️ Advanced Auto-Moderation Bot is active!\n\n"
        "I automatically detect and remove:\n"
        "• Explicit 18+ content\n"
        "• Child exploitation material\n"
        "• Violent/graphic content\n\n"
        "Admins can use /detectsticker to analyze stickers"
    )

def main():
    """Start the bot"""
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
    app.add_handler(CommandHandler("detectsticker", detect_sticker))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🤖 Bot is starting...")
    logger.info(f"🔍 Using policy: Explicit threshold={policy.explicit_threshold}")
    
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
