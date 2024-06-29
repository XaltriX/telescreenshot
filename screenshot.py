import telebot
import os
import re
import tempfile
import requests
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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

# Helper function to create a cancel button
def get_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('Cancel'))
    return keyboard

# Handler to start the bot and choose feature
@bot.message_handler(commands=['start'])
def start_message(message):
    if not is_user_allowed(message):
        return
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = KeyboardButton("Custom Caption")
    button2 = KeyboardButton("TeraBox Editor")
    keyboard.add(button1, button2)
    bot.send_message(message.chat.id, "Welcome! Please choose a feature:", reply_markup=keyboard)

# Handler to process text messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_user_allowed(message):
        return
    if message.text == "Custom Caption":
        keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("Manual Preview", "Auto Preview", "Cancel")
        bot.send_message(message.chat.id, "Please choose preview type:", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_preview_type)
    elif message.text == "TeraBox Editor":
        bot.send_message(message.chat.id, "Please send one or more images, videos, or GIFs with TeraBox links in the captions.")
    elif message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

def handle_preview_type(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    user_id = message.chat.id
    if message.text == "Manual Preview":
        user_data[user_id] = {"preview_type": "manual"}
        bot.send_message(user_id, "Please provide the manual preview link:", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(message, handle_manual_preview)
    elif message.text == "Auto Preview":
        user_data[user_id] = {"preview_type": "auto"}
        bot.send_message(user_id, "Please send a video to generate the preview.", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(message, process_video)
    else:
        bot.send_message(user_id, "Invalid choice. Please try again.")
        bot.register_next_step_handler(message, handle_preview_type)

def handle_manual_preview(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        user_data[user_id]["preview_link"] = message.text
        bot.send_message(user_id, "Please provide a custom caption for the video.", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(message, handle_caption)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Handler to process the video for custom caption
def process_video(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    if message.video:
        user_id = message.chat.id
        file_id = message.video.file_id
        file_info = bot.get_file(file_id)
        
        # Download progress
        download_msg = bot.send_message(user_id, "Downloading video: 0%")
        downloaded_file = bot.download_file(file_info.file_path)
        bot.edit_message_text("Downloading video: 100%", user_id, download_msg.message_id)
        
        temp_file_path = None
        collage_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file.write(downloaded_file)
                temp_file_path = temp_file.name
            
            # Generate screenshots progress
            screenshot_msg = bot.send_message(user_id, "Generating screenshots: 0%")
            screenshots = generate_screenshots(temp_file_path, user_id, screenshot_msg.message_id)
            try:
                bot.edit_message_text("Generating screenshots: 100%", user_id, screenshot_msg.message_id)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    raise
            
            collage = create_collage(screenshots)
            collage_path = f"{temp_file_path}_collage.jpg"
            collage.save(collage_path, optimize=True, quality=95)
            
            # Upload progress
            upload_msg = bot.send_message(user_id, "Uploading to graph.org: 0%")
            graph_url = upload_to_graph(collage_path, user_id, upload_msg.message_id)
            bot.edit_message_text("Uploading to graph.org: 100%", user_id, upload_msg.message_id)
            
            user_data[user_id]["preview_link"] = graph_url
            
            bot.send_message(user_id, "Preview generated. Please provide a custom caption for the video.", reply_markup=get_cancel_keyboard())
            bot.register_next_step_handler(message, handle_caption)
        except Exception as e:
            bot.send_message(user_id, f"An error occurred: {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if collage_path and os.path.exists(collage_path):
                os.unlink(collage_path)
    else:
        bot.send_message(message.chat.id, "Please send a video. Try again or type 'Cancel' to exit.", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(message, process_video)

def generate_screenshots(video_file, user_id, message_id):
    clip = VideoFileClip(video_file)
    duration = clip.duration
    num_screenshots = 5 if duration < 60 else 10
    time_points = np.linspace(0, duration, num_screenshots, endpoint=False)
    
    screenshots = []
    for i, time_point in enumerate(time_points):
        frame = clip.get_frame(time_point)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        screenshot = resize_and_add_watermark(frame)
        screenshots.append(screenshot)
        progress = int((i + 1) / num_screenshots * 100)
        bot.edit_message_text(f"Generating screenshots: {progress}%", user_id, message_id)
    
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

def upload_to_graph(image_path, user_id, message_id):
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
    if message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        user_data[user_id]["caption"] = message.text
        bot.send_message(message.chat.id, "Please provide a link to add in the caption or type 'Cancel' to exit.", reply_markup=get_cancel_keyboard())
        bot.register_next_step_handler(message, handle_link)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Handler to handle the link provided by the user
def handle_link(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
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
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("18+ Bot🤖🔞", url="https://t.me/new_leakx_mms_bot"))
        keyboard.add(InlineKeyboardButton("More Videos🔞🎥", url="https://t.me/+H6sxjIpsz-cwYjQ0"))
        keyboard.add(InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send back the cover photo with the custom caption and buttons
        try:
            bot.send_photo(user_id, THUMBNAIL_URL, caption=formatted_caption, reply_markup=keyboard)
        except Exception as e:
            bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        finally:
            # Cleanup user_data
            del user_data[user_id]
            # Restart the process for the next post
            start_message(message)
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

        with open(media_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Process the caption
        original_caption = message.caption or ""
        processed_caption = process_terabox_link(original_caption)

        # Create an inline keyboard
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("18+ Bot🤖🔞", url="https://t.me/new_leakx_mms_bot"))
        keyboard.add(InlineKeyboardButton("More Videos🔞🎥", url="https://t.me/+H6sxjIpsz-cwYjQ0"))
        keyboard.add(InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send the media with the processed caption and inline keyboard
        if media_type == 'photo':
            with open(media_filename, 'rb') as photo:
                bot.send_photo(user_id, photo, caption=processed_caption, reply_markup=keyboard)
        elif media_type == 'video':
            with open(media_filename, 'rb') as video:
                bot.send_video(user_id, video, caption=processed_caption, reply_markup=keyboard)
        elif media_type == 'gif':
            with open(media_filename, 'rb') as gif:
                bot.send_document(user_id, gif, caption=processed_caption, reply_markup=keyboard)

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(media_filename):
            os.remove(media_filename)

def process_terabox_link(caption):
    # Regular expression to match TeraBox links
    terabox_pattern = r'(https?://(?:www\.)?terabox\.com/[^\s]+)'
    
    # Find all TeraBox links in the caption
    terabox_links = re.findall(terabox_pattern, caption)
    
    # Process each TeraBox link
    for link in terabox_links:
        # Generate the modified link
        modified_link = f"https://teraboxapp.com/s/{link.split('/')[-1]}"
        
        # Replace the original link with the modified link in the caption
        caption = caption.replace(link, modified_link)
    
    return caption

# Start the bot
bot.polling()
