import os
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import asyncio
import aiohttp
import tempfile
import json

# Set up the Telegram bot
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'  # Bot token included directly
bot = telegram.Bot(token=TOKEN)

async def start(update: telegram.Update, context: CallbackContext) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! Send me a video to generate a screenshot collage.")

async def screenshot(update: telegram.Update, context: CallbackContext) -> None:
    if not update.message or not update.message.video:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a video.")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            file_id = update.message.video.file_id
            file_name = os.path.join(temp_dir, f"{file_id}.mp4")

            await download_video(context, update.effective_chat.id, file_id, file_name)
            screenshots = await generate_screenshots(file_name, update, context)
            collage = create_collage(screenshots)
            collage_path = os.path.join(temp_dir, f"collage_{file_id}.jpg")
            collage.save(collage_path, optimize=True, quality=95)

            graph_url = await upload_to_graph(collage_path)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Here's your screenshot collage: {graph_url}")

        except Exception as e:
            error_message = f"Error: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            print(error_message)

async def download_video(context, chat_id, file_id, file_name):
    new_file = await context.bot.get_file(file_id)
    file_path = new_file.file_path
    file_size = new_file.file_size
    chunk_size = 1024 * 1024  # 1 MB

    progress_message = await context.bot.send_message(chat_id=chat_id, text="Downloading video... 0%")
    previous_progress = 0

    async with aiohttp.ClientSession() as session:
        async with session.get(file_path) as response:
            with open(file_name, 'wb') as f:
                downloaded_size = 0
                async for chunk in response.content.iter_chunked(chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress = int(10 * downloaded_size / file_size)
                    if progress != previous_progress:
                        bar = "▰" * progress + "═" * (10 - progress)
                        await context.bot.edit_message_text(chat_id=chat_id, message_id=progress_message.message_id, 
                                                            text=f"Downloading video... {bar} {progress * 10}%")
                        previous_progress = progress

async def generate_screenshots(video_file: str, update: telegram.Update, context: CallbackContext) -> list[Image.Image]:
    clip = VideoFileClip(video_file)
    width, height = int(clip.w), int(clip.h)
    duration = clip.duration
    num_screenshots = 5 if duration < 60 else 10
    time_points = np.linspace(0, duration, num_screenshots, endpoint=False)

    progress_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Generating screenshots... 0%")
    previous_progress = 0

    screenshots = []
    for i, time_point in enumerate(time_points):
        frame = clip.get_frame(time_point)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = adjust_color_balance(frame)
        screenshot = resize_and_add_watermark(frame, width, height)
        screenshots.append(screenshot)

        progress = int(10 * (i + 1) / num_screenshots)
        if progress != previous_progress:
            bar = "▰" * progress + "═" * (10 - progress)
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=progress_message.message_id, 
                                                text=f"Generating screenshots... {bar} {(i+1)*10}%")
            previous_progress = progress

    clip.close()
    return screenshots

import numpy as np

import cv2

def adjust_color_balance(frame):
    # Convert the frame to the HSV color space
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # Adjust the saturation and value channels
    hsv_frame[:, :, 1] = hsv_frame[:, :, 1] * 0.9  # Reduce saturation by 10%
    hsv_frame[:, :, 2] = hsv_frame[:, :, 2] * 0.95  # Reduce value (brightness) by 5%

    # Convert the frame back to the RGB color space
    adjusted_frame = cv2.cvtColor(hsv_frame, cv2.COLOR_HSV2RGB)
    return adjusted_frame



def resize_and_add_watermark(frame, original_width, original_height):
    frame_width = 640
    frame_height = int(original_height * frame_width / original_width)
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

async def upload_to_graph(image_path):
    url = "https://graph.org/upload"
    
    async with aiohttp.ClientSession() as session:
        with open(image_path, "rb") as file:
            form = aiohttp.FormData()
            form.add_field('file', file)
            async with session.post(url, data=form) as response:
                if response.status == 200:
                    data = await response.json()
                    if data[0].get("src"):
                        return f"https://graph.org{data[0]['src']}"
                    else:
                        raise Exception("Unable to retrieve image link from response")
                else:
                    raise Exception(f"Upload failed with status code {response.status}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, screenshot))
    
    application.run_polling()

if __name__ == "__main__":
    main()
