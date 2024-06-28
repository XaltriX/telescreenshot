import telebot
import os
import re
import tempfile
import requests
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Your Telegram Bot API token
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Permanent thumbnail URL for the custom caption feature
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'

# Dictionary to store user data for custom captions
user_data = {}

# Allowed user (your Telegram username without '@')
ALLOWED_USER = 'i_am_yamraj'

# Helper function to check if the user is allowed
def is_user_allowed(message):
    user = bot.get_chat(message.chat.id)
    if user.username != ALLOWED_USER:
        bot.send_message(message.chat.id, "This is a personal bot. If you want to make your own bot, please contact the developer @i_am_yamraj.")
        return False
    return True

# Handler to start the bot and choose feature
@bot.message_handler(commands=['start'])
def start_message(message):
    if not is_user_allowed(message):
        return
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = telebot.types.KeyboardButton("Custom Caption")
    button2 = telebot.types.KeyboardButton("TeraBox Editor")
    button3 = telebot.types.KeyboardButton("Cancel")
    keyboard.add(button1, button2, button3)
    bot.send_message(message.chat.id, "Welcome! Please choose a feature:", reply_markup=keyboard)

# Handler to process text messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_user_allowed(message):
        return
    if message.text == "Custom Caption":
        bot.send_message(message.chat.id, "Please send a video to generate the preview.")
        bot.register_next_step_handler(message, process_video)
    elif message.text == "TeraBox Editor":
        bot.send_message(message.chat.id, "Please send one or more images, videos, or GIFs with TeraBox links in the captions.")
    elif message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

# Handler to process the video for custom caption
def process_video(message):
    if not is_user_allowed(message):
        return
    if message.video:
        user_id = message.chat.id
        file_id = message.video.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(downloaded_file)
            temp_file_path = temp_file.name
        
        try:
            screenshots = generate_screenshots(temp_file_path)
            collage = create_collage(screenshots)
            collage_path = f"{temp_file_path}_collage.jpg"
            collage.save(collage_path, optimize=True, quality=95)
            
            graph_url = upload_to_graph(collage_path)
            user_data[user_id] = {"preview_link": graph_url}
            
            bot.send_message(user_id, "Preview generated. Please provide a custom caption for the video or type 'Cancel' to exit.")
            bot.register_next_step_handler(message, handle_caption)
        finally:
            os.unlink(temp_file_path)
            if os.path.exists(collage_path):
                os.unlink(collage_path)
    else:
        bot.send_message(message.chat.id, "Please send a video. Try again or type 'Cancel' to exit.")
        bot.register_next_step_handler(message, process_video)

def generate_screenshots(video_file):
    clip = VideoFileClip(video_file)
    duration = clip.duration
    num_screenshots = 5 if duration < 60 else 10
    time_points = np.linspace(0, duration, num_screenshots, endpoint=False)
    
    screenshots = []
    for time_point in time_points:
        frame = clip.get_frame(time_point)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        screenshot = resize_and_add_watermark(frame)
        screenshots.append(screenshot)
    
    clip.close()
    return screenshots

def resize_and_add_watermark(frame):
    frame_width = 640
    frame_height = int(frame.shape[0] * frame_width / frame.shape[1])
    resized_frame = cv2.resize(frame, (frame_width, frame_height), interpolation=cv2.INTER_LANCZOS4)
    
    screenshot = Image.fromarray(resized_frame)
    draw = ImageDraw.Draw(screenshot)
    font = ImageFont.load_default()
    text = "@NeonGhost_Networks"
    text_x = (frame_width - 200) // 2
    text_y = (frame_height - 20) // 2
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))
    
    return screenshot

def create_collage(screenshots):
    cols = 2
    rows = (len(screenshots) + 1) // 2
    collage_width = 640 * cols
    collage_height = 360 * rows
    collage = Image.new('RGB', (collage_width, collage_height))
    
    for i, screenshot in enumerate(screenshots):
        x = (i % cols) * 640
        y = (i // cols) * 360
        collage.paste(screenshot.resize((640, 360)), (x, y))
    
    return collage

def upload_to_graph(image_path):
    url = "https://graph.org/upload"
    
    with open(image_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data[0].get("src"):
            return f"https://graph.org{data[0]['src']}"
        else:
            raise Exception("Unable to retrieve image link from response")
    else:
        raise Exception(f"Upload failed with status code {response.status_code}")

# Handler to handle the custom caption provided by the user
def handle_caption(message):
    if not is_user_allowed(message):
        return
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        caption = message.text
        user_data[user_id]["caption"] = caption
        bot.send_message(message.chat.id, "Please provide a link to add in the caption or type 'Cancel' to exit.")
        bot.register_next_step_handler(message, handle_link)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Handler to handle the link provided by the user
def handle_link(message):
    if not is_user_allowed(message):
        return
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        preview_link = user_data[user_id]["preview_link"]
        caption = user_data[user_id]["caption"]
        link = message.text

        # Format the caption with the preview link and the custom link
        formatted_caption = (
            f"◇──◆──◇──◆  ◇──◆──◇──◆\n"
            f"   @NeonGhost_Networks\n"
            f"◇──◆──◇──◆  ◇──◆──◇──◆\n\n"
            f"╰┈┈➤ 🚨 {caption} 🚨\n\n"
            f"╰┈┈┈┈┈➤ 🔗 Preview Link: {preview_link}\n\n"
            f"╰┈┈┈┈┈┈┈┈➤ 💋 🔗🤞 Full Video Link: {link} 🔞🤤\n"
        )

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("18+ Bot🤖🔞", url="https://t.me/new_leakx_mms_bot"))
        keyboard.add(telebot.types.InlineKeyboardButton("More Videos🔞🎥", url="https://t.me/+H6sxjIpsz-cwYjQ0"))
        keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send back the cover photo with the custom caption and buttons
        try:
            bot.send_photo(user_id, THUMBNAIL_URL, caption=formatted_caption, reply_markup=keyboard)
        except Exception as e:
            bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        finally:
            # Cleanup user_data
            del user_data[user_id]
            # Restart the process for the next post
            bot.send_message(user_id, "Please send a video for the next post or type 'Cancel' to exit.")
            bot.register_next_step_handler(message, process_video)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Handler to process images, videos, and GIFs with captions (TeraBox Editor)
@bot.message_handler(content_types=['photo', 'video', 'document'])
def handle_media(message):
    if not is_user_allowed(message):
        return
    user_id = message.chat.id
    media_type = message.content_type

    if media_type == 'photo':
        process_media(message, 'photo')
    elif media_type == 'video':
        process_media(message, 'video')
    elif media_type == 'document':
        # Check if the document is a GIF
        if message.document.mime_type == 'image/gif':
            process_media(message, 'gif')
        else:
            bot.send_message(message.chat.id, "Unsupported document type. Please send images, videos, or GIFs.")
    else:
        bot.send_message(message.chat.id, "Unsupported media type. Please send images, videos, or GIFs.")

def process_media(message, media_type):
    user_id = message.chat.id

    try:
        if media_type == 'photo':
            file_id = message.photo[-1].file_id
        elif media_type == 'video':
            file_id = message.video.file_id
        elif media_type == 'gif':
            file_id = message.document.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the file to a local path
        if media_type == 'photo':
            media_filename = f"media_{file_id}.jpg"
        elif media_type == 'video':
            media_filename = f"media_{file_id}.mp4"
        elif media_type == 'gif':
            media_filename = f"media_{file_id}.gif"

        with open(media_filename, 'wb') as media_file:
            media_file.write(downloaded_file)

        # Use regex to find any link containing "terabox" in the caption
        text = message.caption  # Get the caption text
        if not text:
            bot.send_message(user_id, "No caption provided. Please start again by typing /start.")
            return

        # Use regex to find all links containing "terabox" in the caption
        terabox_links = re.findall(r'https?://\S*terabox\S*', text, re.IGNORECASE)
        if not terabox_links:
            bot.send_message(user_id, "No valid TeraBox link found in the caption. Please try again.")
            return

        # Format the caption with the TeraBox links
        formatted_caption = (
            f"⚝─────⭒─⭑─⭒──────⚝\n"
            "  👉  ​🇼​​🇪​​🇱​​🇨​​🇴​​🇲​​🇪​❗ 👈\n"
            " ⚝─────⭒─⭑─⭒──────⚝\n\n"
            "≿━━━━━━━༺❀༻━━━━━━≾\n"
            f"📥  𝐉𝐎𝐈𝐍 𝐔𝐒 :– @NeonGhost_Networks\n"
            "≿━━━━━━━༺❀༻━━━━━━≾\n\n"
        )

        if len(terabox_links) == 1:
            formatted_caption += f"➽───❥🔗𝐅𝐮𝐥𝐥 𝐕𝐢𝐝𝐞𝐨 𝐋𝐢𝐧𝐤:🔗 {terabox_links[0]}\n\n"
        else:
            for idx, link in enumerate(terabox_links, start=1):
                formatted_caption += f"➽───❥🔗𝐕𝐢𝐝𝐞𝐨 𝐋𝐢𝐧𝐤 {idx}:🔗 {link}\n\n"

        formatted_caption += "─❚█═𝑩𝒚 𝑵𝒆𝒐𝒏𝑮𝒉𝒐𝒔𝒕 𝑵𝒆𝒕𝒘𝒐𝒓𝒌𝒔═█❚─"

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("How To Watch & Download 🔞", url="https://t.me/HTDTeraBox/5"))
        keyboard.add(telebot.types.InlineKeyboardButton("Movie Group🔞🎥", url="https://t.me/RequestGroupNG"))
        keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send back the media with the TeraBox links and buttons
        with open(media_filename, 'rb') as media:
            if media_type == 'photo':
                bot.send_photo(user_id, media, caption=formatted_caption, reply_markup=keyboard)
            elif media_type == 'video':
                bot.send_video(user_id, media, caption=formatted_caption, reply_markup=keyboard)
            elif media_type == 'gif':
                bot.send_document(user_id, media, caption=formatted_caption, reply_markup=keyboard)

    except Exception as e:
        bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")

    finally:
        # Remove the local file after sending
        if os.path.exists(media_filename):
            os.remove(media_filename)

# Start polling for messages
bot.polling()
