import os
import io
import logging
import asyncio
import aiofiles
from tempfile import NamedTemporaryFile
from PIL import Image
from telegram import Message
import ffmpeg

# Setup logging
logger = logging.getLogger(__name__)

# Minimum dimensions for processing
MIN_WIDTH = 200
MIN_HEIGHT = 200

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
    """Convert WEBP sticker to high-quality JPG format"""
    try:
        logger.debug(f"Converting WEBP to JPG: {webp_path}")
        async with aiofiles.open(webp_path, 'rb') as f:
            img_data = await f.read()
        
        with Image.open(io.BytesIO(img_data)) as img:
            # Enhance small stickers
            if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                scale_factor = max(MIN_WIDTH/img.width, MIN_HEIGHT/img.height)
                new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                img = img.resize(new_size, Image.LANCZOS)
                logger.debug(f"Upscaled sticker: {img.width}x{img.height}")
            
            with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                img.convert("RGB").save(jpg_file.name, "JPEG", quality=95, optimize=True)
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

async def extract_video_frames(video_path: str) -> list:
    """Extract multiple frames from video sticker using FFmpeg"""
    try:
        logger.debug(f"Extracting frames from video: {video_path}")
        
        # Get video duration
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        logger.debug(f"Video duration: {duration}s")
        
        # Determine frame extraction points
        if duration > 3:
            timestamps = [0.0, duration/3, 2*duration/3, duration-0.5]
        else:
            timestamps = [0.0, duration/2]
        
        frames = []
        for i, timestamp in enumerate(timestamps):
            with NamedTemporaryFile(delete=False, suffix=f"_{i}.jpg") as frame_file:
                try:
                    (
                        ffmpeg
                        .input(video_path, ss=timestamp)
                        .filter('scale', MIN_WIDTH, -1)  # Ensure minimum width
                        .output(frame_file.name, vframes=1, q:v=2)
                        .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                    )
                    logger.debug(f"Extracted video frame at {timestamp}s: {frame_file.name}")
                    frames.append(frame_file.name)
                except ffmpeg.Error as e:
                    logger.error(f"FFmpeg error: {e.stderr.decode()}")
        
        return frames
    except Exception as e:
        logger.error(f"Video frame extraction failed: {str(e)}", exc_info=True)
        return []
    finally:
        # Cleanup original video file
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
            logger.debug(f"Cleaned up video file: {video_path}")

async def convert_tgs_to_frames(tgs_path: str) -> list:
    """Convert animated sticker to multiple frames using Lottie"""
    try:
        logger.debug(f"Converting TGS sticker: {tgs_path}")
        
        # Create temp directory for frames
        temp_dir = "tgs_frames"
        os.makedirs(temp_dir, exist_ok=True)
        png_pattern = os.path.join(temp_dir, "frame_%03d.png")
        
        # Build conversion command
        cmd = [
            "lottie_convert.py",
            tgs_path,
            png_pattern
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
                logger.error(f"Lottie failed: {stderr.decode().strip()}")
                return []
            
            # Get all generated frames
            frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.png')])
            
            # Select key frames (first, middle, last)
            if len(frame_files) > 3:
                selected_indices = [0, len(frame_files)//2, -1]
                frame_files = [frame_files[i] for i in selected_indices]
            
            jpg_files = []
            for frame_file in frame_files:
                png_path = os.path.join(temp_dir, frame_file)
                with Image.open(png_path) as img:
                    # Enhance small stickers
                    if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                        scale_factor = max(MIN_WIDTH/img.width, MIN_HEIGHT/img.height)
                        new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                        img.convert("RGB").save(jpg_file.name, "JPEG", quality=95, optimize=True)
                        jpg_files.append(jpg_file.name)
                        logger.debug(f"Converted TGS frame: {jpg_file.name}")
            
            return jpg_files
        except asyncio.TimeoutError:
            logger.warning("Lottie conversion timed out")
            return []
    except Exception as e:
        logger.error(f"Animated sticker conversion failed: {str(e)}", exc_info=True)
        return []
    finally:
        # Cleanup temporary files
        if tgs_path and os.path.exists(tgs_path):
            os.remove(tgs_path)
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

async def process_media(message: Message, bot) -> list:
    """Process media and return list of image paths for classification"""
    try:
        # Process images
        if message.photo:
            logger.info("Processing photo message")
            file_id = message.photo[-1].file_id  # Get highest resolution
            path = await download_media(bot, file_id)
            return [path] if path else []
        
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
                    return []
                jpg_path = await convert_webp_to_jpg(webp_path)
                return [jpg_path] if jpg_path else []
            
            # Video sticker (WEBM)
            elif sticker.is_video:
                logger.debug("Processing video sticker")
                webm_path = await download_media(bot, sticker.file_id, "webm")
                if not webm_path:
                    return []
                return await extract_video_frames(webm_path)
            
            # Animated sticker (TGS)
            elif sticker.is_animated:
                logger.debug("Processing animated sticker")
                tgs_path = await download_media(bot, sticker.file_id, "tgs")
                if not tgs_path:
                    return []
                return await convert_tgs_to_frames(tgs_path)
        
        logger.warning("Unsupported media type")
        return []
    except Exception as e:
        logger.error(f"Media processing failed: {str(e)}", exc_info=True)
        return []
