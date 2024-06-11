import os
from pyrogram import Client, filters
from telegraph import upload_file
import logging
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API credentials
API_ID = 24955235
API_HASH = 'f317b3f7bbe390346d8b46868cff0de8'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

# Initialize the bot
bot = Client("screenshot_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Set FFmpeg path
FFMPEG_PATH = "/app/bin/ffmpeg"

# Function to generate screenshots and upload to Telegraph
async def process_video(message):
    try:
        # Download the video
        video_path = await bot.download_media(message)
        screenshots = []

        # Generate screenshots
        for i in range(10):
            screenshot_path = f"screenshot_{i}.jpg"
            os.system(f"{FFMPEG_PATH} -i {video_path} -vf 'select=not(mod(n\\,{i+1})),scale=320:240' -vframes 1 {screenshot_path}")
            screenshots.append(screenshot_path)

        # Upload screenshots to Telegraph
        telegraph_links = []
        for screenshot in screenshots:
            try:
                response = upload_file(screenshot)
                telegraph_link = f"https://telegra.ph{response[0]}"
                telegraph_links.append(telegraph_link)
            except Exception as e:
                logger.error(f"Failed to upload {screenshot}: {e}")

        # Send Telegraph links to the user
        await message.reply_text("\n".join(telegraph_links))

    except Exception as e:
        logger.error(f"Error processing video: {e}")
    finally:
        # Cleanup
        os.remove(video_path)
        for screenshot in screenshots:
            os.remove(screenshot)

# Handle /start command
@bot.on_message(filters.command("start"))
async def start(client, message):
    buttons = [[
        InlineKeyboardButton('Help', callback_data='help'),
        InlineKeyboardButton('Close', callback_data='close')
    ],
    [
        InlineKeyboardButton('Our Channel', url='http://telegram.me/indusbots'),
        InlineKeyboardButton('Source Code', url='https://github.com/benchamxd/Telegraph-Uploader')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        "<b>Hey there,\n\nI'm a telegraph uploader that can upload photos, videos, and GIFs.\n\nSimply send me a photo, video, or GIF to upload to Telegra.ph.\n\nMade with love by @indusBots</b>",
        reply_markup=reply_markup,
        parse_mode="html"
    )

# Handle video messages
@bot.on_message(filters.video)
async def video_handler(client, message):
    if message.video.file_size < 5242880:  # 5MB limit
        await process_video(message)
    else:
        await message.reply_text("Size should be less than 5MB.")

# Handle GIF messages
@bot.on_message(filters.animation)
async def gif_handler(client, message):
    if message.animation.file_size < 5242880:  # 5MB limit
        await process_video(message)
    else:
        await message.reply_text("Size should be less than 5MB.")

# Handle photo messages
@bot.on_message(filters.photo)
async def photo_handler(client, message):
    msg = await message.reply_text("Trying to download...")
    photo_path = await bot.download_media(message)
    await msg.edit_text("Trying to upload...")
    try:
        response = upload_file(photo_path)
        telegraph_link = f"https://telegra.ph{response[0]}"
        await msg.edit_text(telegraph_link)
    except Exception as e:
        await msg.edit_text(f"Something went wrong: {e}")
    finally:
        os.remove(photo_path)

# Run the bot
bot.run()
