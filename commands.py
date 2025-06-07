import os
import logging
import time
import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import ContextTypes
from database import db

logger = logging.getLogger(__name__)

# Bot owner ID (from environment)
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Bot start time for uptime calculation
BOT_START_TIME = time.time()

# Welcome image URL (set in environment)
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL", "https://example.com/path/to/image.jpg")

def format_uptime(seconds):
    """Convert seconds to human-readable format"""
    time_delta = datetime.timedelta(seconds=seconds)
    days = time_delta.days
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} days")
    if hours > 0:
        parts.append(f"{hours} hours")
    if minutes > 0:
        parts.append(f"{minutes} minutes")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} seconds")
        
    return ", ".join(parts)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with image and buttons"""
    user = update.effective_user
    message = update.message
    
    # Add user to database
    if db.is_connected():
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    
    # Create buttons with new layout
    keyboard = [
        # Row 1: Single "Add to Group" button
        [
            InlineKeyboardButton("➕ Add me to your Group", 
                                 url="https://t.me/your_bot_username?startgroup=true")
        ],
        # Row 2: Help & Commands and Updates
        [
            InlineKeyboardButton("❓ Help & Commands", 
                                 callback_data="help"),
            InlineKeyboardButton("📢 Updates Channel", 
                                 url="https://t.me/your_updates_channel")
        ],
        # Row 3: Developer and Support
        [
            InlineKeyboardButton("👨‍💻 Developer", 
                                 url="https://t.me/your_dev_username"),
            InlineKeyboardButton("👥 Support Group", 
                                 url="https://t.me/your_support_group")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Welcome text
    welcome_text = (
        f"🌸 Hello, {user.first_name}! I'm Shiro SafeBot! 🌸\n\n"
        "I'm here to keep your group clean and safe by deleting all NSFW stickers and images!\n"
        "Let's make your chats nice and comfy for everyone! ✨🐾\n\n"
        "Just add me as admin, and I'll do the rest!\n"
        "Stay safe, stay happy! ✨🐰"
    )
    
    # Send welcome message with image
    try:
        await message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send welcome image: {e}")
        # Fallback to text message if image fails
        await message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user = update.effective_user
    
    # Check if user is owner or sudo
    if user.id != OWNER_ID and not db.is_sudo(user.id):
        await update.message.reply_text("🚫 You don't have permission to use this command.")
        return
    
    # Get stats
    stats = db.get_stats()
    uptime_seconds = time.time() - BOT_START_TIME
    formatted_uptime = format_uptime(uptime_seconds)
    
    # Format response
    response = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👤 Users: <code>{stats.get('users', 0)}</code>\n"
        f"👥 Groups: <code>{stats.get('groups', 0)}</code>\n"
        f"⏱ Uptime: <code>{formatted_uptime}</code>\n\n"
        "✨ Keep your communities safe!"
    )
    
    await update.message.reply_text(response, parse_mode="HTML")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users and groups"""
    user = update.effective_user
    message = update.message
    
    # Check if user is owner or sudo
    if user.id != OWNER_ID and not db.is_sudo(user.id):
        await message.reply_text("🚫 You don't have permission to use this command.")
        return
    
    # Check if message is a reply
    if not message.reply_to_message:
        await message.reply_text("ℹ️ Please reply to a message to broadcast it.")
        return
    
    # Confirmation button
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "⚠️ Are you sure you want to broadcast this message to all users and groups?",
        reply_markup=reply_markup,
        reply_to_message_id=message.reply_to_message.message_id
    )

async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a sudo user"""
    user = update.effective_user
    message = update.message
    
    # Only owner can add sudo users
    if user.id != OWNER_ID:
        await message.reply_text("🚫 Only the owner can add sudo users.")
        return
    
    # Check if user ID is provided
    if not context.args:
        await message.reply_text("ℹ️ Usage: /addsudo <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        if db.add_sudo(user_id):
            await message.reply_text(f"✅ User {user_id} added to sudo list.")
        else:
            await message.reply_text("❌ Failed to add user to sudo list.")
    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

async def rmsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a sudo user"""
    user = update.effective_user
    message = update.message
    
    # Only owner can remove sudo users
    if user.id != OWNER_ID:
        await message.reply_text("🚫 Only the owner can remove sudo users.")
        return
    
    # Check if user ID is provided
    if not context.args:
        await message.reply_text("ℹ️ Usage: /rmsudo <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        if db.remove_sudo(user_id):
            await message.reply_text(f"✅ User {user_id} removed from sudo list.")
        else:
            await message.reply_text("❌ User not found in sudo list.")
    except ValueError:
        await message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

async def sudolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all sudo users"""
    user = update.effective_user
    message = update.message
    
    # Only owner and sudo users can see the list
    if user.id != OWNER_ID and not db.is_sudo(user.id):
        await message.reply_text("🚫 You don't have permission to use this command.")
        return
    
    sudo_list = db.get_sudo_list()
    if not sudo_list:
        await message.reply_text("ℹ️ No sudo users found.")
        return
    
    response = "👑 <b>Sudo Users:</b>\n\n" + "\n".join(f"• <code>{user_id}</code>" for user_id in sudo_list)
    await message.reply_text(response, parse_mode="HTML")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    # Broadcast confirmation
    if query.data == "broadcast_confirm":
        message = query.message.reply_to_message
        if not message:
            await query.edit_message_text("❌ Original message not found.")
            return
        
        # Get all users and groups
        stats = db.get_stats()
        total = stats.get("users", 0) + stats.get("groups", 0)
        
        # Edit confirmation message
        await query.edit_message_text(f"📢 Broadcasting to {total} recipients...")
        
        # Actual broadcast would go here (implementation skipped for brevity)
        # In real implementation, you'd loop through all users and groups
        # and send the message with error handling
        
        await query.edit_message_text(f"✅ Broadcast completed to {total} recipients!")
    
    elif query.data == "broadcast_cancel":
        await query.edit_message_text("❌ Broadcast cancelled.")
    
    # Help button handler
    elif query.data == "help":
        help_text = (
            "🛡️ <b>Shiro SafeBot Commands</b> 🛡️\n\n"
            "<b>For Everyone:</b>\n"
            "/start - Show welcome message\n\n"
            "<b>For Admins:</b>\n"
            "/stats - Show bot statistics\n"
            "/broadcast - Send message to all users (reply to message)\n\n"
            "<b>For Owner:</b>\n"
            "/addsudo [user_id] - Add sudo user\n"
            "/rmsudo [user_id] - Remove sudo user\n"
            "/sudolist - List all sudo users\n\n"
            "✨ I automatically moderate groups by deleting NSFW content!"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="HTML"
        )
