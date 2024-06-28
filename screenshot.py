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
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("Manual Preview", "Auto Preview")
        keyboard.add("Cancel")
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
    user_id = message.chat.id
    if message.text == "Manual Preview":
        user_data[user_id] = {"preview_type": "manual"}
        bot.send_message(user_id, "Please provide the manual preview link:")
        bot.register_next_step_handler(message, handle_manual_preview)
    elif message.text == "Auto Preview":
        user_data[user_id] = {"preview_type": "auto"}
        bot.send_message(user_id, "Please send a video to generate the preview.")
        bot.register_next_step_handler(message, process_video)
    elif message.text == "Cancel":
        bot.send_message(message.chat.id, "Process canceled. Please choose a feature from the menu.")
        start_message(message)
    else:
        bot.send_message(user_id, "Invalid choice. Please try again.")
        bot.register_next_step_handler(message, handle_preview_type)

def handle_manual_preview(message):
    if not is_user_allowed(message):
        return
    user_id = message.chat.id
    if user_id in user_data:
        user_data[user_id]["preview_link"] = message.text
        bot.send_message(user_id, "Please provide a custom caption for the video.")
        bot.register_next_step_handler(message, handle_caption)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

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
            user_data[user_id]["preview_link"] = graph_url
            
            bot.send_message(user_id, "Preview generated. Please provide a custom caption for the video.")
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
        user_data[user_id]["caption"] = message.text
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
            f"🔗 Preview: [here]({preview_link})\n"
            f"🔗 Link: [here]({link})\n\n"
            f"⚡️ @NeonGhost_Networks\n"
            f"⚡️ @NeonGhost_Networks\n"
        )

        bot.send_message(message.chat.id, "Caption with link formatted. Here is the preview:", disable_web_page_preview=False)
        bot.send_message(message.chat.id, formatted_caption, disable_web_page_preview=False)

        # Clean up user data
        user_data.pop(user_id, None)
        bot.send_message(message.chat.id, "Process completed. Please choose a feature from the menu.")
        start_message(message)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Start the bot
bot.polling()
