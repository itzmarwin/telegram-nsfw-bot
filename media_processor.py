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
            logger.debug(f"Downloaded media to {temp_file.name}")
            return temp_file.name
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

async def convert_webp_to_jpg(webp_path: str) -> str:
    """Convert WEBP sticker to JPG format"""
    try:
        with Image.open(webp_path) as img:
            with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                img.convert("RGB").save(jpg_file.name, "JPEG", quality=90)
                logger.debug(f"Converted WEBP to JPG: {jpg_file.name}")
                return jpg_file.name
    except Exception as e:
        logger.error(f"WEBP conversion failed: {e}")
        return None
    finally:
        # Cleanup original WEBP file
        if webp_path and os.path.exists(webp_path):
            os.remove(webp_path)

async def extract_video_frame(video_path: str) -> str:
    """Extract first frame from video sticker using FFmpeg"""
    try:
        with NamedTemporaryFile(delete=False, suffix=".jpg") as frame_file:
            # Use subprocess_exec for better security
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vframes", "1",       # Capture only 1 frame
                "-q:v", "2",           # Quality level (2-31, 2=best)
                frame_file.name,
                "-y"                   # Overwrite output
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Wait for process to complete with timeout
            try:
                await asyncio.wait_for(process.communicate(), timeout=15)
            except asyncio.TimeoutError:
                logger.warning("FFmpeg frame extraction timed out")
                process.kill()
                return None
                
            if process.returncode != 0:
                logger.error(f"FFmpeg failed with code {process.returncode}")
                return None
                
            logger.debug(f"Extracted video frame: {frame_file.name}")
            return frame_file.name
    except Exception as e:
        logger.error(f"Video frame extraction failed: {e}")
        return None
    finally:
        # Cleanup original video file
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

async def convert_tgs_to_frame(tgs_path: str) -> str:
    """Convert animated sticker to static frame using Lottie"""
    try:
        with NamedTemporaryFile(delete=False, suffix=".png") as png_file:
            cmd = ["lottie_convert.py", tgs_path, png_file.name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Wait for conversion
            try:
                await asyncio.wait_for(process.communicate(), timeout=20)
            except asyncio.TimeoutError:
                logger.warning("Lottie conversion timed out")
                process.kill()
                return None
                
            if process.returncode != 0:
                logger.error(f"Lottie failed with code {process.returncode}")
                return None
                
            # Convert PNG to JPG
            with Image.open(png_file.name) as img:
                with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                    img.convert("RGB").save(jpg_file.name, "JPEG", quality=90)
                    logger.debug(f"Converted TGS to JPG: {jpg_file.name}")
                    return jpg_file.name
    except Exception as e:
        logger.error(f"Animated sticker conversion failed: {e}")
        return None
    finally:
        # Cleanup temporary files
        if tgs_path and os.path.exists(tgs_path):
            os.remove(tgs_path)
        if 'png_file' in locals() and os.path.exists(png_file.name):
            os.remove(png_file.name)

async def process_media(message: Message, bot) -> str:
    """Process different media types and return image path for classification"""
    # Process images
    if message.photo:
        logger.info("Processing photo")
        file_id = message.photo[-1].file_id  # Get highest resolution
        return await download_media(bot, file_id)
    
    # Process stickers
    if message.sticker:
        sticker = message.sticker
        logger.info(f"Processing sticker: animated={sticker.is_animated}, video={sticker.is_video}")
        
        # Static sticker (WEBP)
        if not sticker.is_animated and not sticker.is_video:
            logger.debug("Processing static sticker")
            webp_path = await download_media(bot, sticker.file_id, "webp")
            return await convert_webp_to_jpg(webp_path) if webp_path else None
        
        # Video sticker (WEBM)
        elif sticker.is_video:
            logger.debug("Processing video sticker")
            webm_path = await download_media(bot, sticker.file_id, "webm")
            return await extract_video_frame(webm_path) if webm_path else None
        
        # Animated sticker (TGS)
        elif sticker.is_animated:
            logger.debug("Processing animated sticker")
            tgs_path = await download_media(bot, sticker.file_id, "tgs")
            return await convert_tgs_to_frame(tgs_path) if tgs_path else None
    
    return None
