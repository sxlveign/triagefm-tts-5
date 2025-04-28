"""
triage.fm - A Telegram bot for generating podcast scripts and audio from read-it-later content
"""
import os
import logging
import textwrap
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import custom modules
from content_processor import ContentProcessor
from script_generator import ScriptGenerator
from database import Database
from tts_processor import TTSProcessor

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize global objects
db = Database()
content_processor = ContentProcessor()
script_generator = ScriptGenerator()
tts_processor = TTSProcessor()

# Constants
MAX_MESSAGE_LENGTH = 4000  # Telegram's limit is 4096, but we'll use a smaller value to be safe

# Messages
WELCOME_MESSAGE = (
    "Hi {first_name}! I'm triage.fm, your personal podcast delivery service.\n\n"
    "Just send me links, documents, or text content, and I'll add them to your queue.\n\n"
    "When you're ready, use the /generate command to create a podcast from your content."
)

HELP_MESSAGE = (
    "Here's how to use triage.fm:\n\n"
    "1. Send me any content you want to process: links, documents, or text.\n"
    "2. I'll confirm when I've received and processed each item.\n"
    "3. When you're ready, use /generate to create a podcast with both script and audio.\n\n"
    "Available commands:\n"
    "/start - Start the bot\n"
    "/help - Show this help message\n"
    "/generate - Create a podcast from your content\n"
    "/queue - See what's in your content queue\n"
    "/clear - Clear your content queue"
)

GENERATING_MESSAGE = "I'm creating your audio podcast now. This may take a minute..."
EMPTY_QUEUE_MESSAGE = "You don't have any new content to process. Send me some links or documents first!"
ERROR_MESSAGE = "Sorry, I encountered an error while generating your podcast. Please try again later."
AUDIO_ERROR_MESSAGE = "Sorry, I couldn't generate the audio podcast at this time. Please try again later."
QUEUE_EMPTY_MESSAGE = "Your content queue is empty. Send me some links or documents to get started!"
QUEUE_HEADER_MESSAGE = "Your content queue:"
QUEUE_CLEARED_MESSAGE = "Your content queue has been cleared. You can start fresh now!"
CONTENT_RECEIVED_MESSAGE = "Content received and processed! It will be included in your next podcast."
UNSUPPORTED_CONTENT_MESSAGE = "Sorry, {message} Please send other content types."
PROCESSING_ERROR_MESSAGE = "Sorry, I couldn't process that content. Please try again or send a different format."
UNKNOWN_CONTENT_TYPE_MESSAGE = "Sorry, I can't process this type of content yet. Please send me text, links, or documents."
COMMAND_CORRECTION_MESSAGE = "It looks like you're trying to use a command. Please use /{command} instead."
PODCAST_SENT_MESSAGE = "Here's your podcast! Enjoy listening."
SCRIPT_PART_MESSAGE = "Script (Part {part_number}/{total_parts}):"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id

    await update.message.reply_text(WELCOME_MESSAGE.format(first_name=user.first_name))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(HELP_MESSAGE)

async def send_long_message(update: Update, text: str) -> None:
    """
    Split and send a long message that exceeds Telegram's message length limit.
    """
    # Safely escape any potentially harmful HTML
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # Reapply our own safe formatting
    text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")

    # If the message is short enough, send it directly
    if len(text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    # Otherwise, split the message into parts
    parts = textwrap.wrap(text, MAX_MESSAGE_LENGTH, replace_whitespace=False, break_long_words=False)
    total_parts = len(parts)

    # Send each part with a header indicating which part it is
    for i, part in enumerate(parts, 1):
        part_header = SCRIPT_PART_MESSAGE.format(part_number=i, total_parts=total_parts)

        if i == 1:
            # For the first part, just send as is (to include the intro)
            message_text = f"{part}"
        else:
            # For subsequent parts, add a continuation header
            message_text = f"{part_header}\n\n{part}"

        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a podcast from the user's content queue."""
    user_id = update.effective_user.id

    # Check if there's content in the queue
    content_queue = db.get_unprocessed_content(user_id)
    if not content_queue:
        await update.message.reply_text(EMPTY_QUEUE_MESSAGE)
        return

    # Send generating message
    status_message = await update.message.reply_text(GENERATING_MESSAGE)

    try:
        # Generate script
        formatted_script, plain_script, tts_script = script_generator.generate_script(user_id, content_queue)

        # Save scripts to files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_dir = f"data/scripts/{user_id}"
        os.makedirs(script_dir, exist_ok=True)

        # Save all versions of the script
        with open(f"{script_dir}/formatted_{timestamp}.html", 'w') as f:
            f.write(formatted_script)
        with open(f"{script_dir}/plain_{timestamp}.txt", 'w') as f:
            f.write(plain_script)
        with open(f"{script_dir}/tts_{timestamp}.txt", 'w') as f:
            f.write(tts_script)

        audio_generated = False
        try:
            # Generate and send only the audio
            audio_path = tts_processor.generate_audio(tts_script)

            with open(audio_path, 'rb') as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    caption="Your podcast is ready! Enjoy listening.",
                    title=f"triage.fm podcast - {datetime.now().strftime('%Y-%m-%d')}"
                )
            audio_generated = True

            # Clean up the audio file after sending
            try:
                os.remove(audio_path)
                logger.info(f"Deleted temporary audio file: {audio_path}")
            except Exception as e:
                logger.error(f"Error deleting audio file: {str(e)}")

        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            warning = ("Note: Due to high server load, the audio version couldn't be generated this time. "
                      "You can try generating it again in a few minutes using the /generate command.")
            await update.message.reply_text(warning)

        # Generate content summaries with ADHD-friendly formatting
        summary_message = "🎙️ PODCAST SUMMARY\n━━━━━━━━━━━━━━━\n\n"
        for i, item in enumerate(content_queue, 1):
            title = item.get('title', 'Untitled')
            author = item.get('author', 'Unknown Author')
            source_url = item.get('source_url', '')
            message_id = item.get('message_id', '')

            # Generate a focused 1-2 sentence summary for each item
            try:
                summary = script_generator.generate_content_summary(item)
            except Exception:
                content = item.get('content', '')
                summary = content[:200] + '...' if len(content) > 200 else content

            # Format the item link
            if source_url:
                link = source_url
            elif message_id:
                link = f"t.me/c/{abs(user_id)}/{message_id}"
            else:
                link = "No link available"

            # Create visually structured item summary with emojis and clear sections
            summary_message += f"📎 ITEM {i}\n"
            summary_message += f"━━━━━━━━━━━━━━━\n"
            summary_message += f"📗 Title: {title}\n"
            summary_message += f"✍️ Author: {author}\n"
            summary_message += f"💡 Insights: {summary}\n"
            summary_message += f"🔗 Link: {link}\n\n"

        # Add audio status to summary if there was an error
        if not audio_generated:
            summary_message += "\n⚠️ Audio version not available at this time. Try /generate again in a few minutes."

        # Send summary message
        await update.message.reply_text(summary_message, disable_web_page_preview=True)

        # Mark content as processed
        content_ids = [item['id'] for item in content_queue]
        db.mark_content_as_processed(user_id, content_ids)

        # Delete the status message
        await status_message.delete()

    except Exception as e:
        logger.error(f"Error generating podcast: {str(e)}")
        await update.message.reply_text(ERROR_MESSAGE)
        await status_message.delete()

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's content queue."""
    user_id = update.effective_user.id
    # Get unprocessed content
    unprocessed_content = db.get_unprocessed_content(user_id)
    if not unprocessed_content:
        await update.message.reply_text(QUEUE_EMPTY_MESSAGE)
        return

    # Create readable content type mapping
    content_type_display = {
        'youtube_video': '📺 YouTube Video',
        'web_article': '📄 Web Article',
        'document': '📝 Document',
        'plain_text': '✍️ Text Note',
        'forwarded': '↪️ Forwarded Message',
        'unknown': '❓ Unknown Type'
    }

    # Format queue message
    queue_message = f"{QUEUE_HEADER_MESSAGE}\n\n"
    for i, item in enumerate(unprocessed_content, 1):
        title = item.get('title', 'Untitled content')
        content_type = item.get('content_type', 'unknown')
        readable_type = content_type_display.get(content_type, '❓ Unknown Type')
        queue_message += f"{i}. {title} [{readable_type}]\n"
    
    # Use send_long_message to handle potentially long messages
    await send_long_message(update, queue_message)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the user's content queue."""
    user_id = update.effective_user.id

    # Clear unprocessed content
    db.clear_unprocessed_content(user_id)

    await update.message.reply_text(QUEUE_CLEARED_MESSAGE)

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user message to extract and store content."""
    user_id = update.effective_user.id
    message = update.message

    logger.info(f"Processing message from user {user_id}: {message.text}")

    # Handle commands that might be missing the slash
    if message.text and not message.text.startswith('/'):
        lowercase_text = message.text.lower()
        if lowercase_text in ['start', 'help', 'generate', 'queue', 'clear']:
            await update.message.reply_text(COMMAND_CORRECTION_MESSAGE.format(command=lowercase_text))
            return

    # Check for message properties to determine content type
    content_item = None

    # Process text from the message, even if it has photos
    if message.text or message.caption:
        # Use caption if text is None (for messages with photos)
        text_content = message.text if message.text else message.caption
        if text_content:
            logger.info(f"Processing text content: {text_content}")
            # Check if it's a text-only message or contains a URL
            content_item = content_processor.process_text(
                text_content, 
                user_id,
                message_id=message.message_id,
                is_forwarded=bool(message.forward_from or message.forward_from_chat)
            )
            logger.info(f"Content processing result: {content_item}")

    # Process document
    elif message.document:
        logger.info(f"Processing document: {message.document.file_name}")
        # Get file from Telegram
        file = await message.document.get_file()
        file_path = f"temp/{message.document.file_id}"
        await file.download_to_drive(file_path)

        content_item = content_processor.process_document(
            file_path, 
            message.document.file_name, 
            user_id
        )

        # Clean up temp file
        os.remove(file_path)

    # Unknown content type
    else:
        logger.warning(f"Unknown content type for message: {message}")
        await message.reply_text(UNKNOWN_CONTENT_TYPE_MESSAGE)
        return

    # Handle content processing result
    if content_item and content_item.get('success'):
        logger.info(f"Successfully processed content: {content_item.get('title', 'No title')}")
        # Store content in database
        if db.add_content(content_item):
            await message.reply_text(CONTENT_RECEIVED_MESSAGE)
        else:
            await message.reply_text("This content is already in your queue. I'll skip adding it again.")
    elif content_item and content_item.get('unsupported'):
        logger.warning(f"Unsupported content: {content_item.get('message', 'No message')}")
        await message.reply_text(
            UNSUPPORTED_CONTENT_MESSAGE.format(message=content_item.get('message', 'this content type is not supported yet'))
        )
    else:
        logger.error(f"Failed to process content: {content_item}")
        await message.reply_text(PROCESSING_ERROR_MESSAGE)

def main() -> None:
    """Start the bot."""
    # Create application
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables")
        return

    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("clear", clear_command))

    # Add message handler for content - including photos and all types that might have captions
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.FORWARDED, 
        process_message
    ))

    # Start the Bot
    application.run_polling()

if __name__ == "__main__":
    # Create temp directories if they don't exist
    os.makedirs("temp", exist_ok=True)
    os.makedirs("temp/audio", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Initialize database
    db.initialize()

    # Clean up old audio files on startup
    tts_processor = TTSProcessor()
    tts_processor.cleanup_old_files()

    # Start the bot
    main()