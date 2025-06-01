import os
import logging
import asyncio
import aiofiles
from tempfile import NamedTemporaryFile
from PIL import Image
from telegram import Message

# Setup logging
logger = logging.getLogger(__name__)

async def download_media(bot, file_id: str, ext: str = "jpg") -> str:
    """Download media file and return temporary file path"""
    try:
        logger.debug(f"Downloading media with file_id: {file_id}")
        media_file = await bot.get_file(file_id)
        temp_file = NamedTemporaryFile(delete=False, suffix=f".{ext}")
        await media_file.download_to_drive(temp_file.name)
        logger.debug(f"Downloaded media to {temp_file.name}")
        return temp_file.name
    except Exception as e:
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        return None

async def convert_webp_to_jpg(webp_path: str) -> str:
    """Convert WEBP sticker to JPG format with cleanup"""
    try:
        logger.debug(f"Converting WEBP to JPG: {webp_path}")
        async with aiofiles.open(webp_path, 'rb') as f:
            img_data = await f.read()
        
        with Image.open(io.BytesIO(img_data)) as img:
            with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                img.convert("RGB").save(jpg_file.name, "JPEG", quality=90, optimize=True)
                logger.debug(f"Converted to JPG: {jpg_file.name}")
                return jpg_file.name
    except Exception as e:
        logger.error(f"WEBP conversion failed: {str(e)}", exc_info=True)
        return None
    finally:
        # Cleanup original WEBP file
        if webp_path and os.path.exists(webp_path):
            os.remove(webp_path)
            logger.debug(f"Cleaned up WEBP file: {webp_path}")

async def extract_video_frame(video_path: str) -> str:
    """Extract first frame from video sticker using FFmpeg with timeout"""
    try:
        logger.debug(f"Extracting frame from video: {video_path}")
        with NamedTemporaryFile(delete=False, suffix=".jpg") as frame_file:
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vframes", "1",       # Capture only 1 frame
                "-q:v", "2",           # Quality level (2-31, 2=best)
                frame_file.name,
                "-y",                  # Overwrite output
                "-loglevel", "error"   # Suppress logs
            ]
            
            # Run FFmpeg with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for process to complete with timeout
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
                if process.returncode != 0:
                    logger.error(f"FFmpeg failed with code {process.returncode}: {stderr.decode().strip()}")
                    return None
                    
                logger.debug(f"Extracted video frame: {frame_file.name}")
                return frame_file.name
            except asyncio.TimeoutError:
                logger.warning("FFmpeg frame extraction timed out")
                try:
                    process.kill()
                    await asyncio.wait_for(process.communicate(), timeout=5)
                except Exception:
                    pass
                return None
    except Exception as e:
        logger.error(f"Video frame extraction failed: {str(e)}", exc_info=True)
        return None
    finally:
        # Cleanup original video file
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
            logger.debug(f"Cleaned up video file: {video_path}")

async def convert_tgs_to_frame(tgs_path: str) -> str:
    """Convert animated sticker to static frame using Lottie"""
    try:
        logger.debug(f"Converting TGS sticker: {tgs_path}")
        png_file = NamedTemporaryFile(delete=False, suffix=".png")
        png_file.close()  # Close so lottie can write to it
        
        # Build conversion command
        cmd = [
            "lottie_convert.py",
            tgs_path,
            png_file.name
        ]
        
        # Run lottie conversion
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Wait for conversion with timeout
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            if process.returncode != 0:
                logger.error(f"Lottie failed with code {process.returncode}: {stderr.decode().strip()}")
                return None
                
            # Convert PNG to JPG
            with Image.open(png_file.name) as img:
                with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                    img.convert("RGB").save(jpg_file.name, "JPEG", quality=90, optimize=True)
                    logger.debug(f"Converted TGS to JPG: {jpg_file.name}")
                    return jpg_file.name
        except asyncio.TimeoutError:
            logger.warning("Lottie conversion timed out")
            try:
                process.kill()
                await asyncio.wait_for(process.communicate(), timeout=5)
            except Exception:
                pass
            return None
    except Exception as e:
        logger.error(f"Animated sticker conversion failed: {str(e)}", exc_info=True)
        return None
    finally:
        # Cleanup temporary files
        if tgs_path and os.path.exists(tgs_path):
            os.remove(tgs_path)
            logger.debug(f"Cleaned up TGS file: {tgs_path}")
        if 'png_file' in locals() and os.path.exists(png_file.name):
            os.remove(png_file.name)
            logger.debug(f"Cleaned up PNG file: {png_file.name}")

async def process_media(message: Message, bot) -> str:
    """Process different media types and return image path for classification"""
    try:
        # Process images
        if message.photo:
            logger.info("Processing photo message")
            file_id = message.photo[-1].file_id  # Get highest resolution
            return await download_media(bot, file_id)
        
        # Process stickers
        if message.sticker:
            sticker = message.sticker
            logger.info(f"Processing sticker: set={sticker.set_name}, "
                       f"animated={sticker.is_animated}, video={sticker.is_video}")
            
            # Static sticker (WEBP)
            if not sticker.is_animated and not sticker.is_video:
                logger.debug("Processing static sticker")
                webp_path = await download_media(bot, sticker.file_id, "webp")
                if not webp_path:
                    return None
                return await convert_webp_to_jpg(webp_path)
            
            # Video sticker (WEBM)
            elif sticker.is_video:
                logger.debug("Processing video sticker")
                webm_path = await download_media(bot, sticker.file_id, "webm")
                if not webm_path:
                    return None
                return await extract_video_frame(webm_path)
            
            # Animated sticker (TGS)
            elif sticker.is_animated:
                logger.debug("Processing animated sticker")
                tgs_path = await download_media(bot, sticker.file_id, "tgs")
                if not tgs_path:
                    return None
                return await convert_tgs_to_frame(tgs_path)
        
        logger.warning("Unsupported media type")
        return None
    except Exception as e:
        logger.error(f"Media processing failed: {str(e)}", exc_info=True)
        return None
