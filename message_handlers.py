import logging
from telegram import Update
from telegram.ext import ContextTypes
from typing import Dict, Set
from datetime import datetime, timedelta
from telegram import ChatPermissions
from difflib import SequenceMatcher

# Set up logging
logger = logging.getLogger(__name__)

# Store deleted message reasons
deleted_messages: Dict[int, str] = {}  # message_id -> reason
edited_message_warnings: Dict[int, int] = {}  # user_id -> warning count

# Bot owner ID
BOT_OWNER_ID = 7798461429

# Store original messages for copyright check
message_history: Dict[int, Dict[int, str]] = {}  # chat_id -> {message_id: text}

# Store copyright protection settings
copyright_enabled: Dict[int, bool] = {}  # chat_id -> enabled/disabled
SIMILARITY_THRESHOLD = 0.85  # 85% similarity threshold

def is_bot_owner(user_id: int) -> bool:
    """Check if the user is the bot owner."""
    return user_id == BOT_OWNER_ID

def get_similarity_ratio(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    return SequenceMatcher(None, text1, text2).ratio()

async def toggle_copyright(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle copyright protection for the chat."""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    
    # Check if user is admin or bot owner
    if not is_bot_owner(update.effective_user.id):
        try:
            chat = await context.bot.get_chat(chat_id)
            admin_ids = [admin.user.id for admin in chat.get_administrators()]
            if update.effective_user.id not in admin_ids:
                await update.message.reply_text("Only admins can toggle copyright protection.")
                return
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return

    # Toggle the setting
    current_state = copyright_enabled.get(chat_id, True)  # Default to enabled
    copyright_enabled[chat_id] = not current_state
    
    status = "enabled" if not current_state else "disabled"
    await update.message.reply_text(f"Copyright protection has been {status} for this chat.")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a message and store the reason."""
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text("Please reply to the message you want to delete.")
        return

    # Check if user is bot owner
    if is_bot_owner(update.effective_user.id):
        # Bot owner can delete any message
        try:
            await update.message.reply_to_message.delete()
            await update.message.reply_text("Message deleted by bot owner.")
            return
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            await update.message.reply_text("Failed to delete the message.")
            return

    # Check if user is admin or sudo
    if update.effective_user.id not in context.bot_data.get('admin_ids', set()):
        await update.message.reply_text("You don't have permission to delete messages.")
        return

    # Get the reason for deletion
    reason = " ".join(context.args) if context.args else "No reason provided"
    
    # Store the reason
    deleted_messages[update.message.reply_to_message.message_id] = reason
    
    # Delete the message
    try:
        await update.message.reply_to_message.delete()
        await update.message.reply_text(f"Message deleted.\nReason: {reason}")
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        await update.message.reply_text("Failed to delete the message.")

async def handle_copyright(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle copyright protection for messages."""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    
    # Check if copyright protection is enabled for this chat
    if not copyright_enabled.get(chat_id, True):  # Default to enabled
        return

    # Check if user is bot owner
    if is_bot_owner(update.effective_user.id):
        return  # Allow bot owner to send any message

    message_text = update.message.text

    # Initialize chat history if not exists
    if chat_id not in message_history:
        message_history[chat_id] = {}

    # Check for similar content
    for msg_id, original_text in message_history[chat_id].items():
        similarity = get_similarity_ratio(message_text, original_text)
        if similarity >= SIMILARITY_THRESHOLD:
            try:
                # Delete the copied message
                await update.message.delete()
                
                # Send warning with similarity percentage
                warning_text = (
                    f"⚠️ Copyright Alert\n"
                    f"@{update.effective_user.username}, this message is {similarity:.0%} similar to a previous message.\n"
                    f"Please write more original content."
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=warning_text
                )
                return
            except Exception as e:
                logger.error(f"Error handling copyright: {e}")
                return

    # Store the new message
    message_history[chat_id][update.message.message_id] = message_text

    # Clean up old messages (keep last 100 messages per chat)
    if len(message_history[chat_id]) > 100:
        oldest_msg_id = min(message_history[chat_id].keys())
        del message_history[chat_id][oldest_msg_id]

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages and check for group owner approval."""
    if not update.message or not update.message.sticker:
        return

    # Check if user is bot owner
    if is_bot_owner(update.effective_user.id):
        return  # Allow bot owner to send stickers freely

    try:
        # Get chat information to check group owner
        chat = await context.bot.get_chat(update.effective_chat.id)
        group_owner_id = chat.get_administrators()[0].user.id  # First admin is usually the owner
        
        # Check if user is group owner
        if update.effective_user.id == group_owner_id:
            return  # Allow group owner to send stickers freely

        # Check if user is approved for stickers
        sticker_approved_users = context.bot_data.get('sticker_approved_users', set())
        if update.effective_user.id in sticker_approved_users:
            return  # Allow approved users to send stickers

        # Delete the sticker and notify user
        await update.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"@{update.effective_user.username}, stickers require group owner approval. Please contact the group owner."
        )
    except Exception as e:
        logger.error(f"Error handling sticker: {e}")

async def approve_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve a user to send stickers (group owner only)."""
    if not context.args:
        await update.message.reply_text("Please provide a user ID to approve for stickers.")
        return

    # Check if user is bot owner
    if is_bot_owner(update.effective_user.id):
        try:
            user_id = int(context.args[0])
            sticker_approved_users = context.bot_data.get('sticker_approved_users', set())
            sticker_approved_users.add(user_id)
            context.bot_data['sticker_approved_users'] = sticker_approved_users
            await update.message.reply_text(f"User {user_id} has been approved to send stickers.")
            return
        except ValueError:
            await update.message.reply_text("Invalid user ID provided.")
            return

    try:
        # Get chat information to check group owner
        chat = await context.bot.get_chat(update.effective_chat.id)
        group_owner_id = chat.get_administrators()[0].user.id  # First admin is usually the owner

        # Check if user is group owner
        if update.effective_user.id != group_owner_id:
            await update.message.reply_text("Only the group owner can approve users for stickers.")
            return

        user_id = int(context.args[0])
        sticker_approved_users = context.bot_data.get('sticker_approved_users', set())
        sticker_approved_users.add(user_id)
        context.bot_data['sticker_approved_users'] = sticker_approved_users
        await update.message.reply_text(f"User {user_id} has been approved to send stickers.")
    except ValueError:
        await update.message.reply_text("Invalid user ID provided.")
    except Exception as e:
        logger.error(f"Error in approve_sticker: {e}")
        await update.message.reply_text("An error occurred while trying to approve the user.")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle edited messages by deleting them without warnings."""
    if not update.edited_message:
        return

    # Check if user is bot owner
    if is_bot_owner(update.effective_user.id):
        return  # Allow bot owner to edit messages freely

    # Check if user is admin or sudo
    if update.effective_user.id in context.bot_data.get('admin_ids', set()):
        return  # Allow admins to edit messages freely

    try:
        # Delete the edited message
        await update.edited_message.delete()
        
        # Send a simple notification
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"@{update.effective_user.username}, message editing is not allowed. Please send a new message instead."
        )
            
    except Exception as e:
        logger.error(f"Error handling edited message: {e}") 