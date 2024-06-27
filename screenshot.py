import os
import time
import asyncio
import requests
from moviepy.editor import VideoFileClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from telegraph import upload_file
from telegram import Update
from telegram.ext import CallbackContext, ApplicationBuilder, CommandHandler, MessageHandler, filters

# Add your bot token here
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

async def generate_screenshots(video_file: str, update: Update, context: CallbackContext) -> list:
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

        screenshots = []
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
                    text = "@NeonGhost_Networks"
                    text_x = (frame_width - 200) // 2
                    text_y = (frame_height - 20) // 2
                    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))
                    
                    screenshots.append(screenshot)
                    
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
        
        return screenshots
    except FileNotFoundError as e:
        error_message = f"Error generating screenshots: {str(e)}\nMake sure the video file '{video_file}' exists and has the correct permissions."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e
    except Exception as e:
        error_message = f"Error in generate_screenshots function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
        raise e

async def upload_screenshots(screenshots: list, update: Update, context: CallbackContext):
    try:
        links = []
        for screenshot in screenshots:
            screenshot_path = f"./temp/{update.effective_chat.id}_{time.time()}.jpg"
            screenshot.save(screenshot_path)
            with open(screenshot_path, 'rb') as file:
                response = requests.post('https://graph.org/upload', files={'file': file})
                response_data = response.json()
                if response.status_code == 200 and response_data.get('src'):
                    links.append(f"https://graph.org{response_data['src']}")
            os.remove(screenshot_path)
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Screenshots uploaded to graph.org:\n" + "\n".join(links))
    except Exception as e:
        error_message = f"Error uploading screenshots: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)

async def screenshot(update: Update, context: CallbackContext):
    video = update.message.video
    video_file_path = f"./temp/{video.file_id}.mp4"
    
    await update.message.video.get_file().download(custom_path=video_file_path)
    
    try:
        screenshots = await generate_screenshots(video_file_path, update, context)
        await upload_screenshots(screenshots, update, context)
        os.remove(video_file_path)
    except Exception as e:
        error_message = f"Error in screenshot function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send me a video to generate and upload screenshots.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, screenshot))
    
    application.run_polling()

if __name__ == "__main__":
    main()
