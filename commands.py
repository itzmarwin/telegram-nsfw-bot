import os
import logging
import time
import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes
from telegram.constants import ChatType
from database import db

logger = logging.getLogger(__name__)

# Bot owner ID (from environment)
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Bot start time for uptime calculation
BOT_START_TIME = time.time()

# Welcome image URL (set in environment)
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL", "https://example.com/path/to/image.jpg")
SUPPORT_GROUP_URL = os.getenv("SUPPORT_GROUP_URL", "https://t.me/your_support_group")

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
    """Enhanced start command with different behavior for private and group chats"""
    user = update.effective_user
    message = update.message
    chat = update.effective_chat
    
    # Add user to database
    if db.is_connected():
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    
    # Private chat - show full welcome with image
    if chat.type == ChatType.PRIVATE:
        # Create buttons with new layout
        keyboard = [
            # Row 1: Single "Add to Group" button
            [
                InlineKeyboardButton("𝗔𝗗𝗗 𝗠𝗘 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗚𝗥𝗢𝗨𝗣", 
                                     url="https://t.me/shirosafebot?startgroup=true")
            ],
            # Row 2: Help & Commands and Updates
            [
                InlineKeyboardButton("𝗛𝗲𝗹𝗽 & 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", 
                                     callback_data="help"),
                InlineKeyboardButton("𝗨𝗽𝗱𝗮𝘁𝗲𝘀", 
                                     url="https://t.me/Samurais_network")
            ],
            # Row 3: Developer and Support
            [
                InlineKeyboardButton("𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿", 
                                     url="https://t.me/Itz_Marv1n"),
                InlineKeyboardButton("𝗦𝘂𝗽𝗽𝗼𝗿𝘁", 
                                     url=SUPPORT_GROUP_URL)
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
    
    # Group chat - show simplified message
    else:
        group_text = (
            "🌸 Hello everyone! I'm Shiro SafeBot! 🌸\n\n"
            "I'm your friendly neighborhood content guardian! 🛡️\n"
            "I keep chats clean and comfy by removing NSFW content automatically.\n\n"
            "Just make me an admin with delete permissions,\n"
            "and I'll handle the rest to keep our space safe and happy! ✨🐰"
        )
        
        # Buttons for group message
        keyboard = [
            [
                InlineKeyboardButton("❌ Close", callback_data="close_message"),
                InlineKeyboardButton("👥 Support", url=SUPPORT_GROUP_URL)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            group_text,
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
    """Add a sudo user with reply support"""
    user = update.effective_user
    message = update.message
    
    # Only owner can add sudo users
    if user.id != OWNER_ID:
        await message.reply_text("🚫 Only the owner can add sudo users.")
        return
    
    # Support replying to messages
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    # Check if user ID is provided
    if not context.args and not target_user:
        await message.reply_text("ℹ️ Usage: /addsudo <user_id> OR reply to a user's message")
        return
    
    try:
        user_id = target_user.id if target_user else int(context.args[0])
        
        # Get user details
        username = target_user.username if target_user else None
        first_name = target_user.first_name if target_user else "Unknown"
        last_name = target_user.last_name if target_user else ""
        
        if db.add_sudo(user_id, username, first_name, last_name):
            await message.reply_text(f"✅ User {first_name} (@{username}) added to sudo list.")
        else:
            await message.reply_text("❌ Failed to add user to sudo list.")
    except (ValueError, TypeError):
        await message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

async def rmsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a sudo user with reply support"""
    user = update.effective_user
    message = update.message
    
    # Only owner can remove sudo users
    if user.id != OWNER_ID:
        await message.reply_text("🚫 Only the owner can remove sudo users.")
        return
    
    # Support replying to messages
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    # Check if user ID is provided
    if not context.args and not target_user:
        await message.reply_text("ℹ️ Usage: /rmsudo <user_id> OR reply to a user's message")
        return
    
    try:
        user_id = target_user.id if target_user else int(context.args[0])
        
        if db.remove_sudo(user_id):
            await message.reply_text(f"✅ User removed from sudo list.")
        else:
            await message.reply_text("❌ User not found in sudo list.")
    except (ValueError, TypeError):
        await message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

async def sudolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all sudo users with names"""
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
    
    response_lines = []
    for sudo in sudo_list:
        name_line = f"• {sudo.get('first_name', '')} {sudo.get('last_name', '')}".strip()
        if not name_line:
            name_line = "Unknown User"
            
        user_line = name_line
        if sudo.get('username'):
            user_line += f" (@{sudo['username']})"
            
        user_line += f" - <code>{sudo['_id']}</code>"
        response_lines.append(user_line)
    
    response = "👑 <b>Sudo Users:</b>\n\n" + "\n".join(response_lines)
    await message.reply_text(response, parse_mode="HTML")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks with proper message editing"""
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
        
        # Get all user IDs and group IDs
        user_ids = db.get_all_user_ids()
        group_ids = db.get_all_group_ids()
        
        # Initialize counters
        success = 0
        failed = 0
        
        # Send to users
        for user_id in user_ids:
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id
                )
                success += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                failed += 1
        
        # Send to groups
        for group_id in group_ids:
            try:
                await context.bot.copy_message(
                    chat_id=group_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id
                )
                success += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to group {group_id}: {e}")
                failed += 1
        
        await query.edit_message_text(
            f"✅ Broadcast completed!\n"
            f"• Successfully sent: {success}\n"
            f"• Failed to send: {failed}"
        )
    
    elif query.data == "broadcast_cancel":
        await query.edit_message_text("❌ Broadcast cancelled.")
    
    # Help button handler
    elif query.data == "help":
        help_text = (
            "🛡️ Shiro SafeBot Commands 🛡️\n\n"
            "For Everyone:\n"
            "/start - Show welcome message\n\n"
            "For Admins:\n"
            "/stats - Show bot statistics\n"
            "/broadcast - Send message to all users (reply to message)\n\n"
            "For Owner:\n"
            "/addsudo [user_id] - Add sudo user\n"
            "/rmsudo [user_id] - Remove sudo user\n"
            "/sudolist - List all sudo users\n\n"
            "✨ I automatically moderate groups by deleting NSFW content!"
        )
        
        # Create back button
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit the original start message to show help
        try:
            await query.edit_message_caption(
                caption=help_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Fallback for text messages
            await query.edit_message_text(
                help_text,
                reply_markup=reply_markup
            )
    
    # Back to start button
    elif query.data == "back_to_start":
        # Recreate original welcome message
        user = query.from_user
        welcome_text = (
            f"🌸 Hello, {user.first_name}! I'm Shiro SafeBot! 🌸\n\n"
            "I'm here to keep your group clean and safe by deleting all NSFW stickers and images!\n"
            "Let's make your chats nice and comfy for everyone! ✨🐾\n\n"
            "Just add me as admin, and I'll do the rest!\n"
            "Stay safe, stay happy! ✨🐰"
        )
        
        # Recreate original buttons
        keyboard = [
            [InlineKeyboardButton("𝗔𝗗𝗗 𝗠𝗘 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗚𝗥𝗢𝗨𝗣", 
                                  url="https://t.me/shirosafebot?startgroup=true")],
            [InlineKeyboardButton("𝗛𝗲𝗹𝗽 & 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", callback_data="help"),
             InlineKeyboardButton("𝗨𝗽𝗱𝗮𝘁𝗲𝘀", 
                                  url="https://t.me/Samurais_network")],
            [InlineKeyboardButton("𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿", 
                                  url="https://t.me/itz_marv1n"),
             InlineKeyboardButton("𝗦𝘂𝗽𝗽𝗼𝗿𝘁", 
                                  url="https://t.me/Anime_group_chat_en")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit back to start
        try:
            # For photo messages
            await query.edit_message_caption(
                caption=welcome_text,
                reply_markup=reply_markup
            )
        except:
            # For text messages
            await query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup
            )
