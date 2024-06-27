 import os
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import asyncio
import aiohttp

# Set up the Telegram bot
TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'  # Hardcoded token
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

            # Check if the video file exists
            if not os.path.isfile(file_name):
                raise FileNotFoundError(f"The video file '{file_name}' does not exist.")
            
            # Generate the screenshots
            screenshots = await generate_screenshots(file_name, update, context)

            # Upload the screenshots to the user
            for i, screenshot in enumerate(screenshots):
                screenshot_path = f"screenshot_{file_id}_{i+1}.png"
                screenshot.save(screenshot_path, optimize=True, quality=95)
                with open(screenshot_path, 'rb') as f:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)
                os.remove(screenshot_path)

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
        # Handle any other exceptions
        error_message = f"Error in screenshot function: {str(e)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        print(error_message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a video.")

async def generate_screenshots(video_file: str, update: telegram.Update, context: CallbackContext) -> list[Image.Image]:
    try:
        # Check if the video file exists
        if not os.path.isfile(video_file):
            raise FileNotFoundError(f"The video file '{video_file}' does not exist or cannot be accessed.")
        
        # Load the video
        clip = VideoFileClip(video_file)
        
        # Get the video dimensions
        width, height = int(clip.w), int(clip.h)
        
        # Get the video duration
        duration = clip.duration
        
        # Determine the number of screenshots based on the video duration
        if duration < 60:  # Less than 1 minute
            num_screenshots = 5
        else:
            num_screenshots = 10
        
        # Calculate the time points for screenshots
        time_points = np.linspace(0, duration, num_screenshots, endpoint=False)
        
        # Send progress indicators for screenshot generation
        screenshot_progress_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Generating screenshots... 0%")
        previous_progress = 0

        # Generate the screenshots
        screenshots = []
        for i, time_point in enumerate(time_points):
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    # Get the frame at the specified time point
                    frame = clip.get_frame(time_point)
                    
                    # Convert the frame to RGB format
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Adjust the color balance to reduce the bluish tone
                    frame_yuv = cv2.cvtColor(frame, cv2.COLOR_RGB2YUV)
                    frame_yuv[:, :, 1] = frame_yuv[:, :, 1] * 0.8
                    frame_yuv[:, :, 2] = frame_yuv[:, :, 2] * 0.8
                    adjusted_frame = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2RGB)
                    
                    # Resize the frame to a fixed size
                    frame_width = 640
                    frame_height = int(height * frame_width / width)
                    resized_frame = cv2.resize(adjusted_frame, (frame_width, frame_height), interpolation=cv2.INTER_LANCZOS4)
                    
                    # Add the watermark to the screenshot
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
                    
                    # Update the progress message
                    progress = int(10 * (i + 1) / num_screenshots)
                    if progress != previous_progress:
                        bar = "▰" * progress + "═" * (10 - progress)
                        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=screenshot_progress_message.message_id, text=f"Generating screenshots... {bar} {(i+1)*10}%")
                        previous_progress = progress
                    await asyncio.sleep(0.5)
                    break  # Exit the retry loop if successful
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
                # If the maximum number of retries is reached, skip the frame
                error_message = f"Skipping frame {i+1} due to multiple errors."
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
                print(error_message)
        
        # Close the video clip
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

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, screenshot))
    
    application.run_polling()

if __name__ == "__main__":
    main()
