import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegraph import Telegraph, upload_file
import ffmpeg

# Your Telegram bot API credentials
API_ID = 24955235
API_HASH = 'f317b3f7bbe390346d8b46868cff0de8'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

app = Client("screenshot_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

telegraph = Telegraph()
telegraph.create_account(short_name='NeonGhost')

# Function to capture screenshots from video
def capture_screenshots(video_path, output_folder, count=10):
    probe = ffmpeg.probe(video_path)
    duration = float(probe['format']['duration'])
    interval = duration / count

    for i in range(count):
        output_path = os.path.join(output_folder, f"screenshot_{i + 1}.jpg")
        (
            ffmpeg
            .input(video_path, ss=i * interval)
            .output(output_path, vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
        )
        yield output_path

# Handler for /start command
@app.on_message(filters.command(["start"]))
async def start(client, message):
    buttons = [
        [
            InlineKeyboardButton('Help', callback_data='help'),
            InlineKeyboardButton('Close', callback_data='close')
        ],
        [
            InlineKeyboardButton('Our Channel', url='http://telegram.me/indusbots'),
            InlineKeyboardButton('Source Code', url='https://github.com/benchamxd/Telegraph-Uploader')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        """<b>Hey there,

I'm a Telegraph Uploader Bot that can upload photos, videos, and GIFs.

Simply send me a photo, video, or GIF to upload to Telegra.ph

Made with love by @indusBots</b>""",
        reply_markup=reply_markup,
        parse_mode="html"
    )

# Handler for video messages
@app.on_message(filters.video)
async def handle_video(client, message):
    if message.video.file_size < 5242880:  # Less than 5MB
        msg = await message.reply_text("`Downloading video...`")
        video_path = await message.download()

        # Create a folder to store screenshots
        user_id = str(message.chat.id)
        output_folder = f"./screenshots/{user_id}"
        os.makedirs(output_folder, exist_ok=True)

        msg = await msg.edit("`Capturing screenshots...`")

        screenshot_paths = list(capture_screenshots(video_path, output_folder))
        links = []

        for path in screenshot_paths:
            try:
                response = upload_file(path)
                link = f"https://telegra.ph{response[0]}"
                links.append(link)
            except Exception as e:
                print(e)

        await msg.edit_text(f"Screenshots:\n" + "\n".join(links))

        # Cleanup
        os.remove(video_path)
        for path in screenshot_paths:
            os.remove(path)
        os.rmdir(output_folder)
    else:
        await message.reply_text("The video file size should be less than 5MB.")

@app.on_callback_query()
async def callback_query_handler(client, callback_query):
    data = callback_query.data
    if data == "help":
        await callback_query.message.edit_text(
            """There is nothing much to know.

Just send me a video/GIF/photo up to 5MB.

I'll upload it to Telegra.ph and give you the direct link.""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Home", callback_data="home"), InlineKeyboardButton("Close", callback_data="close")]
            ])
        )
    elif data == "close":
        await callback_query.message.delete()
    elif data == "home":
        await start(client, callback_query.message)

app.run()
