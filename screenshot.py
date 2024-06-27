import os
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import asyncio
import aiohttp

# Set up the Telegram bot
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'
bot = telegram.Bot(token=TOKEN)

# Define the start command handler
async def start(update: telegram.Update, context: CallbackContext) -> None:
    try:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! Send me a video to generate screenshot collage.")
    except Exception as e:
        error_message = f"Error in start function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)

# Define the screenshot command handler
async def screenshot(update: telegram.Update, context: CallbackContext) -> None:
    try:
        if update.message and update.message.video:
            file_id = update.message.video.file_id
            file_name = f"{file_id}.mp4"

            # Download the video file with progress
            await download_video(file_id, file_name, update, context)

            # Generate the screenshots
            screenshots = await generate_screenshots(file_name, update, context)

            # Upload the screenshots and get the links
            links = await upload_screenshots(screenshots, update, context)

            # Send the links to the user
            if links:
                links_message = "\n".join(links)
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Screenshots uploaded to graph.org:\n{links_message}")

            # Delete the downloaded video file
            os.remove(file_name)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Video file deleted to free up space.")
    except telegram.error.BadRequest as e:
        if "Message is not modified" in str(e):
            # Handle the "Message is not modified" error
            pass
        else:
            # Handle other BadRequest errors
            raise e
    except Exception as e:
        error_message = f"Error in screenshot function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a video.")

async def download_video(file_id: str, file_name: str, update: telegram.Update, context: CallbackContext) -> None:
    try:
        new_file = await context.bot.get_file(file_id)
        file_path = new_file.file_path
        file_size = new_file.file_size
        chunk_size = 1024 * 1024  # 1 MB

        download_progress_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Downloading video... 0%")
        previous_progress = 0

        async with aiohttp.ClientSession() as session:
            async with session.get(file_path) as response:
                downloaded_size = 0
                with open(file_name, 'wb') as f:
                    while True:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress = int(10 * downloaded_size / file_size)
                        if progress != previous_progress:
                            bar = "▰" * progress + "═" * (10 - progress)
                            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=download_progress_message.message_id, text=f"Downloading video... {bar} {progress * 10}%")
                            previous_progress = progress
                        await asyncio.sleep(0.5)
    except Exception as e:
        error_message = f"Error downloading video: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e

async def generate_screenshots(video_file: str, update: telegram.Update, context: CallbackContext) -> list:
    try:
        if not os.path.isfile(video_file):
            raise FileNotFoundError(f"The video file '{video_file}' does not exist or cannot be accessed.")

        clip = VideoFileClip(video_file)
        width, height = int(clip.w), int(clip.h)
        duration = clip.duration
        num_screenshots = 5 if duration < 60 else 10
        time_points = np.linspace(0, duration, num_screenshots, endpoint=False)

        screenshot_progress_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Generating screenshots... 0%")
        previous_progress = 0

        screenshot_paths = []
        for i, time_point in enumerate(time_points):
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    frame = clip.get_frame(time_point)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_yuv = cv2.cvtColor(frame, cv2.COLOR_RGB2YUV)
                    frame_yuv[:, :, 1] = frame_yuv[:, :, 1] * 0.8
                    frame_yuv[:, :, 2] = frame_yuv[:, :, 2] * 0.8
                    adjusted_frame = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2RGB)
                    frame_width = 640
                    frame_height = int(height * frame_width / width)
                    resized_frame = cv2.resize(adjusted_frame, (frame_width, frame_height), interpolation=cv2.INTER_LANCZOS4)

                    screenshot = Image.fromarray(resized_frame)
                    draw = ImageDraw.Draw(screenshot)
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=20)
                    except IOError:
                        font = ImageFont.load_default()
                    text = "@YourWatermark"
                    text_width, text_height = draw.textsize(text, font)
                    text_x = (frame_width - text_width) // 2
                    text_y = frame_height - text_height - 10
                    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

                    screenshot_path = f"screenshot_{update.message.video.file_id}_{i+1}.png"
                    screenshot.save(screenshot_path, optimize=True, quality=95)
                    screenshot_paths.append(screenshot_path)

                    progress = int(10 * (i + 1) / num_screenshots)
                    if progress != previous_progress:
                        bar = "▰" * progress + "═" * (10 - progress)
                        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=screenshot_progress_message.message_id, text=f"Generating screenshots... {bar} {(i+1)*10}%")
                        previous_progress = progress
                    await asyncio.sleep(0.5)
                    break
                except cv2.error as e:
                    error_message = f"Error in generate_screenshots loop (retry {retry_count+1}/{max_retries}): {str(e)}"
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
                    print(error_message)
                    retry_count += 1
                except Exception as e:
                    error_message = f"Error in generate_screenshots loop (retry {retry_count+1}/{max_retries}): {str(e)}"
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
                    print(error_message)
                    retry_count += 1
            else:
                error_message = f"Skipping frame {i+1} due to multiple errors."
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
                print(error_message)

        clip.close()
        return screenshot_paths
    except Exception as e:
        error_message = f"Error in generate_screenshots function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e

async def upload_screenshots(screenshot_paths: list, update: telegram.Update, context: CallbackContext) -> list:
    try:
        links = []
        for screenshot in screenshot_paths:
            link = await upload_to_graph(screenshot, update, context)
            links.append(link)
            os.remove(screenshot)  # Remove the screenshot after upload
        return links
    except Exception as e:
        error_message = f"Error in upload_screenshots function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e

async def upload_to_graph(image_path: str, update: telegram.Update, context: CallbackContext) -> str:
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            async with aiohttp.ClientSession() as session:
                async with session.post('https://telegra.ph/upload', data=files) as response:
                    if response.status == 200:
                        json_response = await response.json()
                        if isinstance(json_response, list) and len(json_response) > 0 and 'src' in json_response[0]:
                            file_path = json_response[0]['src']
                            link = f"https://telegra.ph{file_path}"
                            return link
                    raise ValueError(f"Failed to upload {image_path} to graph.org. Response: {response.status}, {await response.text()}")
    except Exception as e:
        error_message = f"Error in upload_to_graph function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    screenshot_handler = MessageHandler(filters.VIDEO, screenshot)

    application.add_handler(start_handler)
    application.add_handler(screenshot_handler)

    print("Bot is running...")
    application.run_polling()
