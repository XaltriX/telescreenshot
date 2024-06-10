import os
import ffmpeg
import requests
from telegraph import upload_file
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configuration parameters
API_ID = 24955235
API_HASH = 'f317b3f7bbe390346d8b46868cff0de8'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

# Initialize the Telegram Client
Tgraph = Client(
   "Telegra.ph Uploader",
   api_id=API_ID,
   api_hash=API_HASH,
   bot_token=BOT_TOKEN,
)

# Ensure DOWNLOADS directory exists
if not os.path.exists("./DOWNLOADS"):
    os.makedirs("./DOWNLOADS")

# Function to generate screenshots
def generate_screenshots(video_path, output_dir, num_screenshots=10):
    duration = float(ffmpeg.probe(video_path)['format']['duration'])
    interval = duration / (num_screenshots + 1)
    screenshots = []
    for i in range(1, num_screenshots + 1):
        timestamp = i * interval
        screenshot_path = os.path.join(output_dir, f"screenshot_{i}.jpg")
        ffmpeg.input(video_path, ss=timestamp).output(screenshot_path, vframes=1).run()
        screenshots.append(screenshot_path)
    return screenshots

def upload_file_with_retry(file_path, retries=3):
    for attempt in range(retries):
        try:
            return upload_file(file_path)
        except Exception as e:
            if attempt < retries - 1:
                print(f"Upload failed, retrying... ({attempt + 1}/{retries})")
            else:
                raise e

@Tgraph.on_message(filters.video)
async def uploadvid(client, message):
    if message.video.file_size < 52428800:  # 50MB limit
        msg = await message.reply_text("`Trying to download...`")
        userid = str(message.chat.id)
        video_path = f"./DOWNLOADS/{userid}.mp4"
        video_path = await client.download_media(message=message, file_name=video_path)
        await msg.edit_text("`Generating screenshots...`")
        
        try:
            screenshots = generate_screenshots(video_path, "./DOWNLOADS")
            await msg.edit_text("`Uploading screenshots...`")
            
            telegraph_links = []
            for screenshot in screenshots:
                try:
                    tlink = upload_file_with_retry(screenshot)
                    telegraph_links.append(f"https://telegra.ph{tlink[0]}")
                except Exception as e:
                    await msg.edit_text(f"Error uploading screenshot: {str(e)}")
                    return

            telegraph_page_content = '\n'.join(f'<img src="{link}"/>' for link in telegraph_links)
            telegraph_page_content = f'<html><body>{telegraph_page_content}</body></html>'
            
            # Create Telegra.ph page
            response = requests.post('https://api.telegra.ph/createPage', json={
                'title': 'Screenshots',
                'author_name': 'Telegraph Uploader Bot',
                'content': telegraph_page_content
            }).json()
            
            await msg.edit_text(f"Here is your Telegraph link: {response['result']['url']}")
            
            # Cleanup
            os.remove(video_path)
            for screenshot in screenshots:
                os.remove(screenshot)
        except Exception as e:
            await msg.edit_text(f"Something went wrong: {str(e)}")
    else:
        await message.reply_text("Size should be less than 50MB")

@Tgraph.on_message(filters.command(["start"]))
async def home(client, message):
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
    await Tgraph.send_message(
        chat_id=message.chat.id,
        text="<b>Hey there,\n\nI'm a Telegraph Uploader that can upload photos, videos, and GIFs.\n\nSimply send me a photo, video, or GIF to upload to Telegra.ph.\n\nMade with love by @indusBots</b>",
        reply_markup=reply_markup,
        parse_mode="html",
        reply_to_message_id=message.id  # Fixed this line
    )

@Tgraph.on_message(filters.command(["help"]))
async def help(client, message):
    buttons = [
        [
            InlineKeyboardButton('Home', callback_data='home'),
            InlineKeyboardButton('Close', callback_data='close')
        ],
        [
            InlineKeyboardButton('Our Channel', url='http://telegram.me/indusbots')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await Tgraph.send_message(
        chat_id=message.chat.id,
        text="There is nothing more to know.\n\nJust send me a video/GIF/photo up to 50MB.\n\nI'll upload it to Telegra.ph and give you the direct link.",
        reply_markup=reply_markup,
        parse_mode="html",
        reply_to_message_id=message.id  # Fixed this line
    )

@Tgraph.on_callback_query()
async def button(Tgraph, update):
    cb_data = update.data
    if cb_data == "help":
        await update.message.delete()
        await help(Tgraph, update.message)
    elif cb_data == "close":
        await update.message.delete()
    elif cb_data == "home":
        await update.message.delete()
        await home(Tgraph, update.message)

Tgraph.run()
