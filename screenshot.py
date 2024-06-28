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

# Set up the Telegram bot
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'
bot = telegram.Bot(token=TOKEN)

async def start(update: telegram.Update, context: CallbackContext) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! Send me a video to generate screenshots.")

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
            
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Uploading screenshot URLs to a text file...")
            
            screenshot_urls = []
            for i, screenshot in enumerate(screenshots):
                screenshot_path = os.path.join(temp_dir, f"screenshot_{i+1}.jpg")
                screenshot.save(screenshot_path, optimize=True, quality=95)
                
                # Send screenshot to user
                with open(screenshot_path, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=f"Screenshot {i+1}/{len(screenshots)}")
                
                graph_url = await upload_to_graph(screenshot_path)
                screenshot_urls.append(graph_url)
                await context.bot.send_message(chat_id=update.effective_chat.id, 
                                               text=f"Screenshot {i+1}/{len(screenshots)} uploaded to graph.org")

            url_list_path = os.path.join(temp_dir, "screenshot_urls.txt")
            await create_url_list(screenshot_urls, url_list_path)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=open(url_list_path, 'rb'), 
                                            caption="Here is the list of screenshot URLs.")

        except Exception as e:
            error_message = f"Error: {str(e)}\nType: {type(e).__name__}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            print(f"Full error details: {error_message}")
            import traceback
            print(traceback.format_exc())

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

def adjust_color_balance(frame):
    frame_yuv = cv2.cvtColor(frame, cv2.COLOR_RGB2YUV)
    frame_yuv[:, :, 1] = frame_yuv[:, :, 1] * 0.8
    frame_yuv[:, :, 2] = frame_yuv[:, :, 2] * 0.8
    return cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2RGB)

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

async def create_url_list(image_urls, file_path):
    with open(file_path, "w") as f:
        for url in image_urls:
            f.write(url + "\n")

async def upload_to_graph(file_path):
    url = "https://graph.org/upload"
    
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as file:
            form = aiohttp.FormData()
            form.add_field('file', file)
            async with session.post(url, data=form) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Response data: {data}")
                    if isinstance(data, list) and len(data) > 0 and "src" in data[[2]]:
                        return f"https://graph.org{data[[2]]['src']}"
                    else:
                        raise ValueError(f"Unexpected response format. Full response: {data}")
                else:
                    raise Exception(f"Upload failed with status code {response.status}. Response: {await response.text()}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, screenshot))
    
    application.run_polling()

if __name__ == "__main__":
    main()

