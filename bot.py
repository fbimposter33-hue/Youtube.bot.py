#!/usr/bin/env python3
"""
Telegram YouTube Video Downloader Bot
This bot downloads YouTube videos and sends them to Telegram users.
"""

import os
import logging
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TELEGRAM_TOKEN = "8411426585:AAEutDs-nHeMc4XFVy6l9ecJBAvAyxBGlL4"  # Replace with your bot token

# YouTube-DL configuration
ydl_opts = {
    'format': 'best',
    'outtmpl': '%(title)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50 * 1024 * 1024,  # 50MB limit for Telegram
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_message = (
        "🎬 *YouTube Video Downloader Bot*\n\n"
        "Send me a YouTube video URL and I'll download it for you!\n\n"
        "Supported platforms:\n"
        "• YouTube\n"
        "• YouTube Shorts\n"
        "• YouTube Live streams\n\n"
        "⚠️ *Note:* Videos larger than 50MB cannot be sent due to Telegram limits."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_message = (
        "📚 *How to use this bot:*\n\n"
        "1. Copy a YouTube video URL\n"
        "2. Paste it in this chat\n"
        "3. Wait for the download to complete\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "🔗 *Supported URLs:*\n"
        "• youtube.com/watch?v=...\n"
        "• youtu.be/...\n"
        "• youtube.com/shorts/..."
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download YouTube video and send it to the user."""
    url = update.message.text.strip()
    
    # Validate URL
    if not is_valid_youtube_url(url):
        await update.message.reply_text(
            "❌ Please send a valid YouTube URL.\n"
            "Supported formats:\n"
            "• youtube.com/watch?v=...\n"
            "• youtu.be/...\n"
            "• youtube.com/shorts/..."
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("⏳ Processing your request...")
    
    try:
        # Create temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure download options
            download_opts = ydl_opts.copy()
            download_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
            
            # Download video
            with YoutubeDL(download_opts) as ydl:
                # Extract video info first
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                video_ext = info.get('ext', 'mp4')
                video_size = info.get('filesize', 0)
                
                # Check file size
                if video_size and video_size > 50 * 1024 * 1024:
                    await processing_msg.edit_text(
                        f"⚠️ Video is too large ({video_size / (1024*1024):.1f}MB). "
                        "Maximum size is 50MB. Try a shorter video."
                    )
                    return
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_file = None
                for file in os.listdir(temp_dir):
                    if file.endswith(f'.{video_ext}'):
                        downloaded_file = os.path.join(temp_dir, file)
                        break
                
                if downloaded_file and os.path.exists(downloaded_file):
                    # Send the video
                    with open(downloaded_file, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=update.message.chat_id,
                            video=video_file,
                            caption=f"🎬 {video_title}",
                            timeout=120
                        )
                    
                    await processing_msg.edit_text("✅ Video sent successfully!")
                    logger.info(f"Successfully downloaded: {video_title}")
                else:
                    raise Exception("Downloaded file not found")
    
    except DownloadError as e:
        error_msg = f"❌ Error downloading video: {str(e)}"
        await processing_msg.edit_text(error_msg)
        logger.error(f"Download error: {e}")
    
    except Exception as e:
        error_msg = f"❌ An unexpected error occurred: {str(e)}"
        await processing_msg.edit_text(error_msg)
        logger.error(f"Unexpected error: {e}")

def is_valid_youtube_url(url: str) -> bool:
    """Check if the URL is a valid YouTube URL."""
    youtube_patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/live/[\w-]+',
    ]
    
    import re
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Run the bot
    logger.info("Starting YouTube Downloader Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
