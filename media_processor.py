import os
import logging
import asyncio
from tempfile import NamedTemporaryFile
from PIL import Image
from telegram import Message

# Setup logging
logger = logging.getLogger(__name__)

async def download_media(bot, file_id: str, ext: str = "jpg") -> str:
    """Download media file and return temporary file path"""
    try:
        media_file = await bot.get_file(file_id)
        with NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
            await media_file.download_to_drive(temp_file.name)
            return temp_file.name
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

async def convert_webp_to_jpg(webp_path: str) -> str:
    """Convert WEBP sticker to JPG format"""
    try:
        with Image.open(webp_path) as img:
            with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                img.convert("RGB").save(jpg_file.name, "JPEG")
                return jpg_file.name
    except Exception as e:
        logger.error(f"WEBP conversion failed: {e}")
        return None

async def extract_video_frame(video_path: str) -> str:
    """Extract first frame from video sticker using FFmpeg"""
    try:
        with NamedTemporaryFile(delete=False, suffix=".jpg") as frame_file:
            cmd = f"ffmpeg -i {video_path} -vframes 1 -q:v 2 {frame_file.name} -y"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return frame_file.name
    except Exception as e:
        logger.error(f"Video frame extraction failed: {e}")
        return None

async def convert_tgs_to_frame(tgs_path: str) -> str:
    """Convert animated sticker to static frame using Lottie"""
    try:
        with NamedTemporaryFile(delete=False, suffix=".png") as png_file:
            cmd = f"lottie_convert.py {tgs_path} {png_file.name}"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Convert PNG to JPG
            with Image.open(png_file.name) as img:
                with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                    img.convert("RGB").save(jpg_file.name, "JPEG")
                    return jpg_file.name
    except Exception as e:
        logger.error(f"Animated sticker conversion failed: {e}")
        return None

async def process_media(message: Message, bot) -> str:
    """Process different media types and return image path for classification"""
    # Process images
    if message.photo:
        file_id = message.photo[-1].file_id
        return await download_media(bot, file_id)
    
    # Process stickers
    if message.sticker:
        sticker = message.sticker
        
        # Static sticker (WEBP)
        if sticker.is_animated is False and sticker.is_video is False:
            webp_path = await download_media(bot, sticker.file_id, "webp")
            return await convert_webp_to_jpg(webp_path) if webp_path else None
        
        # Video sticker (WEBM)
        elif sticker.is_video:
            webm_path = await download_media(bot, sticker.file_id, "webm")
            return await extract_video_frame(webm_path) if webm_path else None
        
        # Animated sticker (TGS)
        elif sticker.is_animated:
            tgs_path = await download_media(bot, sticker.file_id, "tgs")
            return await convert_tgs_to_frame(tgs_path) if tgs_path else None
    
    return None
