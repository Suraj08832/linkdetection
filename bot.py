import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Set
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
)
from telegram.constants import ChatMemberStatus
from message_handlers import (
    delete_message, 
    handle_sticker, 
    approve_sticker, 
    handle_edited_message,
    handle_copyright,
    toggle_copyright
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global variables to store user data
user_warnings: Dict[int, int] = {}  # user_id -> warning count
approved_users: Set[int] = set()  # Set of approved user IDs
admin_ids: Set[int] = set()  # Set of admin user IDs

# Constants
MAX_WARNINGS = 3
MUTE_DURATION = timedelta(hours=24)  # 24-hour mute

# Autoreply messages
AUTOREPLIES = {
    "what is the rule": "Links in bios are not allowed. Please make sure to follow the group rules.",
    "how can i get approved": "Please contact the group admin for approval.",
    "help": "Please follow the group rules. If you need assistance, ask the admin.",
}

def get_bot_token() -> str:
    """Get the bot token from environment variables with proper error handling."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        token = os.getenv('BOT_TOKEN')  # Try alternative environment variable name
    
    if not token:
        logger.error("No bot token found! Please set TELEGRAM_BOT_TOKEN or BOT_TOKEN environment variable.")
        raise ValueError("Bot token not found in environment variables!")
    
    return token

def extract_links(text: str) -> list:
    """Extract URLs and @ mentions from text using regex."""
    # URL patterns
    url_patterns = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # Regular URLs
        r'www\.[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}',  # URLs without http/https
        r't\.me/[a-zA-Z0-9_]+',  # Telegram links
        r'telegram\.me/[a-zA-Z0-9_]+',  # Alternative Telegram links
        r'instagram\.com/[a-zA-Z0-9_]+',  # Instagram links
        r'@[a-zA-Z0-9_]+',  # @ mentions
        r'https?://(?:www\.)?(?:t\.me|telegram\.me)/[a-zA-Z0-9_]+',  # Telegram links with protocol
        r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_]+',  # Instagram links with protocol
    ]
    
    found_links = []
    for pattern in url_patterns:
        found_links.extend(re.findall(pattern, text, re.IGNORECASE))
    
    return found_links

async def check_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check user's bio for links when they join the group."""
    try:
        if not update.chat_member or not update.chat_member.new_chat_member:
            return

        user = update.chat_member.new_chat_member.user
        logger.info(f"New member joined: {user.username} (ID: {user.id})")
        
        if user.is_bot:
            return

        # Update admin list first
        try:
            chat = await context.bot.get_chat(update.effective_chat.id)
            admin_ids.clear()
            for admin in chat.get_administrators():
                admin_ids.add(admin.user.id)
            logger.info(f"Admin list updated: {admin_ids}")
        except Exception as e:
            logger.error(f"Error updating admin list: {e}")

        # Skip if user is admin
        if user.id in admin_ids:
            logger.info(f"Skipping bio check for admin user: {user.username}")
            return

        # Get user's full info including bio
        try:
            user_info = await context.bot.get_chat(user.id)
            logger.info(f"User bio: {user_info.bio}")
            
            if user_info.bio:
                links = extract_links(user_info.bio)
                logger.info(f"Found links in bio: {links}")
                
                if links and user.id not in approved_users:
                    user_warnings[user.id] = user_warnings.get(user.id, 0) + 1
                    warning_count = user_warnings[user.id]
                    
                    # Create a more detailed warning message
                    warning_message = (
                        f"⚠️ Warning {warning_count}/{MAX_WARNINGS}\n"
                        f"@{user.username} has links in their bio:\n"
                        f"Found: {', '.join(links)}\n"
                        "Please remove all links or reply to this message to request approval."
                    )
                    
                    sent_message = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=warning_message
                    )

                    # Store the warning message ID for later reference
                    context.user_data[f"warning_message_{user.id}"] = sent_message.message_id

                    # Mute user if they reach max warnings
                    if warning_count >= MAX_WARNINGS:
                        await context.bot.restrict_chat_member(
                            chat_id=update.effective_chat.id,
                            user_id=user.id,
                            until_date=datetime.now() + MUTE_DURATION,
                            permissions=ChatPermissions(can_send_messages=False)
                        )
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"🚫 @{user.username} has been muted for 24 hours due to multiple warnings."
                        )
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Unable to check bio for @{user.username}. Please ensure the bot has permission to view user information."
            )
    except Exception as e:
        logger.error(f"Error in check_bio: {e}")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /approve command."""
    logger.info(f"Approve command received from user {update.effective_user.id}")
    if not update.effective_user.id in admin_ids:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a user ID to approve.")
        return

    try:
        user_id = int(context.args[0])
        approved_users.add(user_id)
        user_warnings[user_id] = 0
        await update.message.reply_text(f"User {user_id} has been approved.")
    except ValueError:
        await update.message.reply_text("Invalid user ID provided.")

async def reset_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /reset_warnings command."""
    logger.info(f"Reset warnings command received from user {update.effective_user.id}")
    if not update.effective_user.id in admin_ids:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a user ID to reset warnings.")
        return

    try:
        user_id = int(context.args[0])
        user_warnings[user_id] = 0
        await update.message.reply_text(f"Warnings for user {user_id} have been reset.")
    except ValueError:
        await update.message.reply_text("Invalid user ID provided.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and check for autoreplies."""
    logger.info(f"Message received: {update.message.text}")
    if not update.message or not update.message.text:
        return

    # Check if this is a reply to a warning message
    if update.message.reply_to_message:
        warning_message_id = update.message.reply_to_message.message_id
        user_id = update.effective_user.id
        
        # Check if this is a reply to a warning message
        if context.user_data.get(f"warning_message_{user_id}") == warning_message_id:
            # Check if the user is an admin
            if update.effective_user.id in admin_ids:
                # Admin is approving the user
                approved_users.add(user_id)
                user_warnings[user_id] = 0
                await update.message.reply_text(f"✅ User has been approved by admin.")
            else:
                # User is requesting approval
                await update.message.reply_text(
                    "Your approval request has been sent to the admins. "
                    "Please wait for their response."
                )
                # Notify admins
                for admin_id in admin_ids:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"🔔 Approval request from user @{update.effective_user.username} "
                                 f"(ID: {update.effective_user.id})"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_id}: {e}")

    message_text = update.message.text.lower()
    
    # Check for autoreply triggers
    for trigger, reply in AUTOREPLIES.items():
        if trigger in message_text:
            await update.message.reply_text(reply)
            return

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle channel posts."""
    try:
        if not update.channel_post:
            return

        # Log the channel post
        logger.info(f"Channel post received in {update.effective_chat.title} (ID: {update.effective_chat.id})")
        
        # Check for copyright if enabled
        if context.bot_data.get('copyright_enabled', {}).get(update.effective_chat.id, True):
            await handle_copyright(update, context)
            
    except Exception as e:
        logger.error(f"Error handling channel post: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"Start command received from user {update.effective_user.id}")
    await update.message.reply_text('Hi! I am the Bio Link Bot. I monitor user bios for links and help maintain group rules.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 <b>Bio Link Bot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/info - Show bot information\n"
        "/approve &lt;user_id&gt; - Approve a user's bio link (Admin only)\n"
        "/reset_warnings &lt;user_id&gt; - Reset user warnings (Admin only)\n"
        "/delete &lt;reason&gt; - Delete a message (Admin only, reply to message)\n"
        "/approve_sticker &lt;user_id&gt; - Approve a user to send stickers (Group owner only)\n"
        "/copyright - Toggle copyright protection (Admin only)\n\n"
        "<b>Features:</b>\n"
        "• Monitors user bios for links\n"
        "• Warns users with links in bio\n"
        "• Auto-mutes after 3 warnings\n"
        "• Admin approval system\n"
        "• Message deletion with reasons\n"
        "• Sticker approval system\n"
        "• Copyright protection (85% similarity threshold)\n"
        "• Automatic responses to common queries"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /info is issued."""
    info_text = (
        "🤖 <b>Bot Information</b>\n\n"
        "<b>Core Features:</b>\n"
        "• <b>Bio Link Protection:</b>\n"
        "  - Monitors user bios for links\n"
        "  - Warns users with unapproved links\n"
        "  - Auto-mutes after 3 warnings\n"
        "  - Admin approval system for links\n\n"
        
        "• <b>Message Control:</b>\n"
        "  - Deletes edited messages\n"
        "  - Message deletion with reasons\n"
        "  - Admin-only message deletion\n\n"
        
        "• <b>Sticker Management:</b>\n"
        "  - Group owner approval required\n"
        "  - Admins need approval too\n"
        "  - Auto-deletes unapproved stickers\n\n"
        
        "• <b>Copyright Protection:</b>\n"
        "  - 85% similarity detection\n"
        "  - Auto-deletes copied content\n"
        "  - Shows similarity percentage\n"
        "  - Can be toggled by admins\n\n"
        
        "<b>Special Features:</b>\n"
        "• Bot owner (ID: 7798461429) has full privileges\n"
        "• Automatic responses to common queries\n"
        "• Per-chat settings for copyright protection\n"
        "• Smart warning system with detailed messages\n\n"
        
        "<b>Admin Commands:</b>\n"
        "• /approve - Approve bio links\n"
        "• /reset_warnings - Reset user warnings\n"
        "• /delete - Delete messages with reason\n"
        "• /copyright - Toggle copyright protection\n\n"
        
        "<b>Group Owner Commands:</b>\n"
        "• /approve_sticker - Approve users for stickers\n\n"
        
        "<b>User Commands:</b>\n"
        "• /start - Start the bot\n"
        "• /help - Show help message\n"
        "• /info - Show this information\n\n"
        
        "Bot designed by 𐏓  𝅥‌꯭𝆬ᷟ𝐣‌‌‌➥‌𝗭𝗲‌𝗳𝗿𝗼‌𝗻 ‌🔥❰⎯꯭ ꭗ‌‌  🍂\n"
        "𝐔‌‌𝐬‌‌𝐞‌‌𝐫‌‌𝐧‌‌𝐚‌‌𝐦‌‌𝐞‌‌: @crush_hu_tera"
    )
    await update.message.reply_text(info_text, parse_mode='HTML')

def main() -> None:
    """Start the bot."""
    try:
        # Get bot token
        token = get_bot_token()
        logger.info("Bot token loaded successfully")
        
        # Create the Application
        application = Application.builder().token(token).build()
        logger.info("Application built successfully")

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("info", info_command))
        application.add_handler(CommandHandler("approve", approve_user))
        application.add_handler(CommandHandler("reset_warnings", reset_warnings))
        application.add_handler(CommandHandler("delete", delete_message))
        application.add_handler(CommandHandler("approve_sticker", approve_sticker))
        application.add_handler(CommandHandler("copyright", toggle_copyright))
        
        # Add message handlers
        application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))
        application.add_handler(MessageHandler(filters.UpdateType.EDITED_CHANNEL_POST, handle_edited_message))
        application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, handle_channel_post))
        application.add_handler(MessageHandler(filters.UpdateType.MESSAGE, handle_message))
        application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
        application.add_handler(ChatMemberHandler(check_bio, ChatMemberStatus.MEMBER))

        logger.info("Starting bot...")
        # Start the Bot
        application.run_polling()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main() 