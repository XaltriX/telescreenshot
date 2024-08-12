import telebot
import os
import re
import io
import requests
from PIL import Image, ImageDraw
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data for custom captions
user_data = {}

# Dictionary to store message IDs for deletion
message_ids = {}

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

# Helper function to track messages for deletion
def track_message(user_id, message_id):
    if user_id not in message_ids:
        message_ids[user_id] = []
    message_ids[user_id].append(message_id)

# Helper function to delete tracked messages
def delete_tracked_messages(user_id):
    if user_id in message_ids:
        for msg_id in message_ids[user_id]:
            try:
                bot.delete_message(user_id, msg_id)
            except:
                pass
        message_ids[user_id] = []

# Handler to start the bot and choose feature
@bot.message_handler(commands=['start'])
def start_message(message):
    if not is_user_allowed(message):
        return
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = KeyboardButton("Custom Caption")
    button2 = KeyboardButton("TeraBox Editor")
    keyboard.add(button1, button2)
    msg = bot.send_message(message.chat.id, "Welcome! Please choose a feature:", reply_markup=keyboard)
    track_message(message.chat.id, msg.message_id)

# Handler to process text messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_user_allowed(message):
        return
    if message.text == "Custom Caption":
        keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("Manual Preview", "Auto Preview", "Cancel")
        msg = bot.send_message(message.chat.id, "Please choose preview type:", reply_markup=keyboard)
        track_message(message.chat.id, msg.message_id)
        bot.register_next_step_handler(message, handle_preview_type)
    elif message.text == "TeraBox Editor":
        msg = bot.send_message(message.chat.id, "Please send one or more images, videos, or GIFs with TeraBox links in the captions.")
        track_message(message.chat.id, msg.message_id)
    elif message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
    else:
        msg = bot.send_message(message.chat.id, "Please choose a valid option from the menu.")
        track_message(message.chat.id, msg.message_id)

def handle_preview_type(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
        return
    user_id = message.chat.id
    if message.text == "Manual Preview":
        user_data[user_id] = {"preview_type": "manual"}
        msg = bot.send_message(user_id, "Please provide the manual preview link:", reply_markup=get_cancel_keyboard())
        track_message(user_id, msg.message_id)
        bot.register_next_step_handler(message, handle_manual_preview)
    elif message.text == "Auto Preview":
        user_data[user_id] = {"preview_type": "auto"}
        msg = bot.send_message(user_id, "Please send a video to generate the preview.", reply_markup=get_cancel_keyboard())
        track_message(user_id, msg.message_id)
        bot.register_next_step_handler(message, process_video)
    else:
        msg = bot.send_message(user_id, "Invalid choice. Please try again.")
        track_message(user_id, msg.message_id)
        bot.register_next_step_handler(message, handle_preview_type)

def handle_manual_preview(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        user_data[user_id]["preview_link"] = message.text
        msg = bot.send_message(user_id, "Please provide a custom caption for the video.", reply_markup=get_cancel_keyboard())
        track_message(user_id, msg.message_id)
        bot.register_next_step_handler(message, handle_caption)
    else:
        msg = bot.send_message(message.chat.id, "Please start the process again by typing /start.")
        track_message(message.chat.id, msg.message_id)

def process_video(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
        return
    if message.content_type == 'text':
        msg = bot.send_message(message.chat.id, "Please send a video file, not text. Try again or type 'Cancel' to exit.", reply_markup=get_cancel_keyboard())
        track_message(message.chat.id, msg.message_id)
        bot.register_next_step_handler(message, process_video)
        return
    if message.video:
        user_id = message.chat.id
        file_id = message.video.file_id
        file_info = bot.get_file(file_id)
        file_size = file_info.file_size
        
        if file_size > 20 * 1024 * 1024:
            msg = bot.send_message(user_id, "This video is larger than 20 MB. It may take longer to process.")
            track_message(user_id, msg.message_id)
        
        download_msg = bot.send_message(user_id, "Downloading video: 0%")
        track_message(user_id, download_msg.message_id)
        
        try:
            temp_video_file = f"temp_video_{file_id}.mp4"
            
            # Download the file in chunks
            downloaded_size = 0
            chunk_size = 1024 * 1024  # 1 MB chunks
            last_progress = 0
            with open(temp_video_file, 'wb') as video_file:
                file = bot.download_file(file_info.file_path)
                for chunk in [file[i:i+chunk_size] for i in range(0, len(file), chunk_size)]:
                    video_file.write(chunk)
                    downloaded_size += len(chunk)
                    progress = int(downloaded_size / file_size * 100)
                    if progress - last_progress >= 10:  # Update every 10% progress
                        try:
                            bot.edit_message_text(f"Downloading video: {progress}%", user_id, download_msg.message_id)
                            last_progress = progress
                        except telebot.apihelper.ApiTelegramException as e:
                            if e.error_code != 400 or 'message is not modified' not in e.description:
                                raise
            
            bot.edit_message_text("Video downloaded successfully", user_id, download_msg.message_id)
            
            screenshot_msg = bot.send_message(user_id, "Generating screenshots: 0%")
            track_message(user_id, screenshot_msg.message_id)
            screenshots = generate_screenshots(temp_video_file, user_id, screenshot_msg.message_id)
            bot.edit_message_text("Screenshots generated successfully", user_id, screenshot_msg.message_id)
            
            os.remove(temp_video_file)  # Clean up the temporary video file
            
            collage = create_collage(screenshots)
            collage_buffer = io.BytesIO()
            collage.save(collage_buffer, format='JPEG')
            collage_buffer.seek(0)
            
            collage_msg = bot.send_photo(user_id, collage_buffer, caption="Here's the preview collage:")
            track_message(user_id, collage_msg.message_id)
            
            upload_msg = bot.send_message(user_id, "Uploading to graph.org: 0%")
            track_message(user_id, upload_msg.message_id)
            
            collage_buffer.seek(0)  # Reset buffer position
            graph_url = upload_to_graph(collage_buffer, user_id, upload_msg.message_id)
            bot.edit_message_text("Upload to graph.org completed", user_id, upload_msg.message_id)
            
            user_data[user_id]["preview_link"] = graph_url
            
            msg = bot.send_message(user_id, "Preview generated. Please provide a custom caption for the video.", reply_markup=get_cancel_keyboard())
            track_message(user_id, msg.message_id)
            bot.register_next_step_handler(message, handle_caption)
        except Exception as e:
            error_msg = bot.send_message(user_id, f"An error occurred: {str(e)}")
            track_message(user_id, error_msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, "Please send a video. Try again or type 'Cancel' to exit.", reply_markup=get_cancel_keyboard())
        track_message(message.chat.id, msg.message_id)
        bot.register_next_step_handler(message, process_video)

def generate_screenshots(video_file, user_id, message_id):
    try:
        probe = ffmpeg.probe(video_file)
        duration = float(probe['streams'][0]['duration'])
        num_screenshots = 5 if duration < 60 else 10
        time_points = [i * duration / num_screenshots for i in range(num_screenshots)]
        
        screenshots = []
        for i, time_point in enumerate(time_points):
            output_filename = f"screenshot_{i}.jpg"
            
            try:
                (
                    ffmpeg
                    .input(video_file, ss=time_point)
                    .filter('scale', 640, -1)
                    .output(output_filename, vframes=1)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                screenshot = Image.open(output_filename)
                screenshots.append(screenshot)
                os.remove(output_filename)  # Clean up the temporary file
                
                progress = int((i + 1) / num_screenshots * 100)
                try:
                    bot.edit_message_text(f"Generating screenshots: {progress}%", user_id, message_id)
                except telebot.apihelper.ApiTelegramException as e:
                    if e.error_code != 400 or 'message is not modified' not in e.description:
                        raise
            
            except ffmpeg.Error as e:
                print(f"FFmpeg error: {e.stderr.decode()}")
                raise
    
    except Exception as e:
        print(f"Error in generate_screenshots: {str(e)}")
        raise
    
    return screenshots

def create_collage(screenshots):
    num_screenshots = len(screenshots)
    
    # Determine the orientation based on the first screenshot
    first_screenshot = screenshots[0]
    is_portrait = first_screenshot.height > first_screenshot.width

    # Set collage dimensions and grid layout
    if is_portrait:
        collage_width, collage_height = 1080, 1920
        if num_screenshots == 5:
            grid = (2, 3)
        else:  # 10 screenshots
            grid = (3, 4)
    else:
        collage_width, collage_height = 1920, 1080
        if num_screenshots == 5:
            grid = (3, 2)
        else:  # 10 screenshots
            grid = (4, 3)

    # Calculate cell dimensions
    cell_width = collage_width // grid[0]
    cell_height = collage_height // grid[1]

    # Create a new image with white background
    collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))

    # Minimal separation (1 pixel)
    separation = 1

    for i, screenshot in enumerate(screenshots):
        # Calculate position
        row = i // grid[0]
        col = i % grid[0]
        
        x = col * cell_width + (col * separation)
        y = row * cell_height + (row * separation)
        
        # Resize the screenshot to fit within the cell while maintaining aspect ratio
        img_width = cell_width - separation
        img_height = cell_height - separation
        
        img = screenshot.copy()
        img.thumbnail((img_width, img_height), Image.LANCZOS)
        
        # Center the image in its cell
        x_offset = (cell_width - img.width) // 2
        y_offset = (cell_height - img.height) // 2
        
        collage.paste(img, (x + x_offset, y + y_offset))

    # Add thin lines between cells
    draw = ImageDraw.Draw(collage)
    for i in range(1, grid[0]):
        x = i * cell_width - (separation // 2)
        draw.line([(x, 0), (x, collage_height)], fill=(200, 200, 200), width=separation)
    for j in range(1, grid[1]):
        y = j * cell_height - (separation // 2)
        draw.line([(0, y), (collage_width, y)], fill=(200, 200, 200), width=separation)

    return collage

def upload_to_graph(image_buffer, user_id, message_id):
    url = "https://graph.org/upload"
    
    image_buffer.seek(0)
    files = {"file": ("image.jpg", image_buffer, "image/jpeg")}
    response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data[0].get("src"):
            return f"https://graph.org{data[0]['src']}"
        else:
            raise Exception("Unable to retrieve image link from response")
    else:
        raise Exception(f"Upload failed with status code {response.status_code}")

def handle_caption(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        user_data[user_id]["caption"] = message.text
        msg = bot.send_message(message.chat.id, "Please provide a link to add in the caption or type 'Cancel' to exit.", reply_markup=get_cancel_keyboard())
        track_message(user_id, msg.message_id)
        bot.register_next_step_handler(message, handle_link)
    else:
        msg = bot.send_message(message.chat.id, "Please start the process again by typing /start.")
        track_message(message.chat.id, msg.message_id)

def handle_link(message):
    if not is_user_allowed(message):
        return
    if message.text == "Cancel":
        delete_tracked_messages(message.chat.id)
        start_message(message)
        return
    user_id = message.chat.id
    if user_id in user_data:
        preview_link = user_data[user_id]["preview_link"]
        caption = user_data[user_id]["caption"]
        link = message.text

        formatted_caption = (
            f"◇──◆──◇──◆  ◇──◆──◇──◆\n"
            f"   @NeonGhost_Networks\n"
            f"◇──◆──◇──◆  ◇──◆──◇──◆\n\n"
            f"╰┈┈➤ 🚨 {caption} 🚨\n\n"
            f"╰┈┈┈┈┈➤ 🔗 Preview Link: {preview_link}\n\n"
            f"╰┈┈┈┈┈┈┈┈➤ 💋 🔗🤞 Full Video Link: {link} 🔞🤤\n"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("18+ Bot🤖🔞", url="https://t.me/NightLifeRobot"))
        keyboard.add(InlineKeyboardButton("More Videos🔞🎥", url="https://t.me/+H6sxjIpsz-cwYjQ0"))
        keyboard.add(InlineKeyboardButton("Without Token Video🔞", url="https://t.me/+N2SfuzZQ9h45ZGZk"))
        keyboard.add(InlineKeyboardButton("Movie Group🎥", url="https://t.me/RQSTGroup"))

        try:
            final_post = bot.send_message(user_id, formatted_caption, reply_markup=keyboard)
            delete_tracked_messages(user_id)
            
            # Reset user data while keeping preview type
            preview_type = user_data[user_id]["preview_type"]
            user_data[user_id] = {"preview_type": preview_type}
            
            # Automatically ask for the next video or preview link
            if preview_type == "auto":
                msg = bot.send_message(user_id, "Please send another video to generate the preview.", reply_markup=get_cancel_keyboard())
                track_message(user_id, msg.message_id)
                bot.register_next_step_handler(message, process_video)
            else:
                msg = bot.send_message(user_id, "Please provide another manual preview link:", reply_markup=get_cancel_keyboard())
                track_message(user_id, msg.message_id)
                bot.register_next_step_handler(message, handle_manual_preview)
        except Exception as e:
            error_msg = bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
            track_message(user_id, error_msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, "Please start the process again by typing /start.")
        track_message(message.chat.id, msg.message_id)

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
        if message.document.mime_type == 'image/gif':
            process_media(message, 'gif')
        else:
            msg = bot.send_message(message.chat.id, "Unsupported document type. Please send images, videos, or GIFs.")
            track_message(message.chat.id, msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, "Unsupported media type. Please send images, videos, or GIFs.")
        track_message(message.chat.id, msg.message_id)

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

        if media_type == 'photo':
            media_filename = f"media_{file_id}.jpg"
        elif media_type == 'video':
            media_filename = f"media_{file_id}.mp4"
        elif media_type == 'gif':
            media_filename = f"media_{file_id}.gif"

        with open(media_filename, 'wb') as media_file:
            media_file.write(downloaded_file)

        text = message.caption
        if not text:
            msg = bot.send_message(user_id, "No caption provided. Please start again by typing /start.")
            track_message(user_id, msg.message_id)
            return

        terabox_links = re.findall(r'https?://\S*terabox\S*', text, re.IGNORECASE)
        if not terabox_links:
            msg = bot.send_message(user_id, "No valid TeraBox link found in the caption. Please try again.")
            track_message(user_id, msg.message_id)
            return

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

        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("How To Watch & Download 🔞", url="https://t.me/HTDTeraBox/5"))
        keyboard.add(telebot.types.InlineKeyboardButton("18+ Bot🔞", url="https://t.me/NightLifeRobot"))
        keyboard.add(telebot.types.InlineKeyboardButton("Movie Group", url="https://t.me/RQSTGroup"))

        with open(media_filename, 'rb') as media:
            if media_type == 'photo':
                final_post = bot.send_photo(user_id, media, caption=formatted_caption, reply_markup=keyboard)
            elif media_type == 'video':
                final_post = bot.send_video(user_id, media, caption=formatted_caption, reply_markup=keyboard)
            elif media_type == 'gif':
                final_post = bot.send_document(user_id, media, caption=formatted_caption, reply_markup=keyboard)
        
        delete_tracked_messages(user_id)
        os.remove(media_filename)

    except Exception as e:
        error_msg = bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        track_message(user_id, error_msg.message_id)

# Start the bot
bot.polling()
