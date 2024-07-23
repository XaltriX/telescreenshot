import os
import asyncio
import logging
from typing import List
import tempfile
import requests
from PIL import Image

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified
from moviepy.editor import VideoFileClip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = 28192191
API_HASH = '663164abd732848a90e76e25cb9cf54a'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

# Initialize the Pyrogram client
app = Client("screenshot_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queue to manage multiple video processing tasks
video_queue = asyncio.Queue()

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("Welcome! Send me a video, and I'll generate screenshots for you.")

@app.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    await message.reply_text("Video received. Processing will begin shortly...")
    await video_queue.put(message)

    if video_queue.qsize() == 1:
        asyncio.create_task(process_video_queue())

async def process_video_queue():
    while not video_queue.empty():
        message = await video_queue.get()
        try:
            await process_video(message)
        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            await message.reply_text(f"An error occurred while processing your video: {str(e)}. Please try again later.")
        finally:
            video_queue.task_done()

async def process_video(message: Message):
    video = message.video
    file_id = video.file_id
    file_name = f"{file_id}.mp4"

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)

        # Download the video with progress
        status_message = await message.reply_text("Downloading video: 0%")
        try:
            await download_video_with_progress(message, file_id, video_path, status_message)
        except Exception as e:
            logger.error(f"Error downloading video: {e}", exc_info=True)
            await status_message.edit_text(f"Failed to download the video: {str(e)}. Please try again.")
            return

        # Ask user for number of screenshots
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("5 screenshots", callback_data=f"ss_5_{message.id}"),
             InlineKeyboardButton("10 screenshots", callback_data=f"ss_10_{message.id}")]
        ])
        await status_message.edit_text("How many screenshots do you want?", reply_markup=keyboard)

async def download_video_with_progress(message: Message, file_id: str, file_path: str, status_message: Message):
    async def progress(current, total):
        percent = (current / total) * 100
        try:
            await status_message.edit_text(f"Downloading video: {percent:.1f}%")
        except MessageNotModified:
            pass

    await message.download(file_name=file_path, progress=progress)

@app.on_callback_query()
async def handle_screenshot_choice(client: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data.split('_')
        num_screenshots = int(data[1])
        message_id = int(data[2])
        
        # Retrieve the original message
        message = await app.get_messages(callback_query.message.chat.id, message_id)
        
        file_id = message.video.file_id
        file_name = f"{file_id}.mp4"

        await callback_query.answer()
        status_message = await callback_query.message.edit_text(f"Generating {num_screenshots} screenshots: 0%")

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, file_name)

            # Download the video if it's not already downloaded
            if not os.path.exists(video_path):
                try:
                    await download_video_with_progress(message, file_id, video_path, status_message)
                except Exception as e:
                    logger.error(f"Error downloading video: {e}", exc_info=True)
                    await status_message.edit_text(f"Failed to download the video: {str(e)}. Please try again.")
                    return

            try:
                # Generate screenshots with progress
                screenshots = await generate_screenshots_with_progress(video_path, num_screenshots, temp_dir, status_message)

                await status_message.edit_text("Creating collage...")

                # Create collage
                collage_path = os.path.join(temp_dir, "collage.jpg")
                create_collage(screenshots, collage_path)

                await status_message.edit_text("Uploading collage...")

                # Upload collage to graph.org
                graph_url = await asyncio.to_thread(upload_to_graph, collage_path, callback_query.from_user.id, message_id)

                # Send result to user
                await callback_query.message.reply_text(
                    f"Here is your collage of {num_screenshots} screenshots: {graph_url}",
                    reply_to_message_id=message_id
                )

                await status_message.edit_text("Processing completed.")

            except Exception as e:
                logger.error(f"Error processing video: {e}", exc_info=True)
                await status_message.edit_text(f"An error occurred while processing: {str(e)}. Please try again.")

            finally:
                # Clean up: delete the video file
                if os.path.exists(video_path):
                    os.remove(video_path)
                    logger.info(f"Deleted video file: {video_path}")
    except Exception as e:
        logger.error(f"Error in handle_screenshot_choice: {e}", exc_info=True)
        await callback_query.message.reply_text(f"An unexpected error occurred: {str(e)}. Please try again later.")

async def generate_screenshots_with_progress(video_path: str, num_screenshots: int, output_dir: str, status_message: Message) -> List[str]:
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        interval = duration / (num_screenshots + 1)
        
        screenshots = []
        for i in range(1, num_screenshots + 1):
            time = i * interval
            screenshot_path = os.path.join(output_dir, f"screenshot_{i}.jpg")
            clip.save_frame(screenshot_path, t=time)
            screenshots.append(screenshot_path)
            
            percent = (i / num_screenshots) * 100
            try:
                await status_message.edit_text(f"Generating {num_screenshots} screenshots: {percent:.1f}%")
            except MessageNotModified:
                pass
        
        clip.close()
        return screenshots
    except Exception as e:
        logger.error(f"Error in generate_screenshots_with_progress: {e}", exc_info=True)
        raise

def create_collage(image_paths: List[str], collage_path: str):
    try:
        images = [Image.open(image) for image in image_paths]
        widths, heights = zip(*(i.size for i in images))

        max_width = 800  # Set a maximum width for the collage
        scale = max_width / sum(widths)
        new_widths = [int(w * scale) for w in widths]
        new_heights = [int(h * scale) for h in heights]

        collage = Image.new('RGB', (max_width, max(new_heights)))

        x_offset = 0
        for im, new_width, new_height in zip(images, new_widths, new_heights):
            im_resized = im.resize((new_width, new_height))
            collage.paste(im_resized, (x_offset, 0))
            x_offset += new_width

        collage.save(collage_path)
    except Exception as e:
        logger.error(f"Error in create_collage: {e}", exc_info=True)
        raise

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

async def main():
    await app.start()
    logger.info("Bot started. Listening for messages...")
    await pyrogram.idle()

if __name__ == "__main__":
    app.run(main())
