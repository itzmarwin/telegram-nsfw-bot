import os
import io
import logging
import asyncio
import aiofiles
import cv2
import numpy as np
from tempfile import NamedTemporaryFile
from PIL import Image, ImageEnhance
from telegram import Message
import ffmpeg

logger = logging.getLogger(__name__)

# Enhanced processing parameters
MIN_WIDTH = 300
MIN_HEIGHT = 300
ZOOM_FACTOR = 1.8  # Zoom level for subtle details
ENHANCE_FACTOR = 2.0  # Contrast enhancement

async def download_media(bot, file_id: str, ext: str = "jpg") -> str:
    """Download media with enhanced error handling"""
    try:
        media_file = await bot.get_file(file_id)
        with NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
            await media_file.download_to_drive(temp_file.name)
            return temp_file.name
    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        return None

def enhance_and_zoom(image_path: str) -> list:
    """Create multiple enhanced versions focusing on subtle details"""
    processed_paths = []
    
    try:
        # Original image
        processed_paths.append(image_path)
        
        # Load image
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Create enhanced versions
            for i, enhancement in enumerate(["contrast", "sharpness", "color", "zoom"]):
                with NamedTemporaryFile(delete=False, suffix=f"_{enhancement}.jpg") as temp_file:
                    # Apply different enhancements
                    if enhancement == "contrast":
                        enhancer = ImageEnhance.Contrast(img)
                        enhanced_img = enhancer.enhance(ENHANCE_FACTOR)
                    elif enhancement == "sharpness":
                        enhancer = ImageEnhance.Sharpness(img)
                        enhanced_img = enhancer.enhance(ENHANCE_FACTOR)
                    elif enhancement == "color":
                        enhancer = ImageEnhance.Color(img)
                        enhanced_img = enhancer.enhance(ENHANCE_FACTOR)
                    elif enhancement == "zoom":
                        # Zoom on center with padding
                        zoom_width = int(width / ZOOM_FACTOR)
                        zoom_height = int(height / ZOOM_FACTOR)
                        left = (width - zoom_width) // 2
                        top = (height - zoom_height) // 2
                        right = left + zoom_width
                        bottom = top + zoom_height
                        zoomed = img.crop((left, top, right, bottom))
                        enhanced_img = zoomed.resize((width, height), Image.LANCZOS)
                    
                    enhanced_img.save(temp_file.name, "JPEG", quality=95)
                    processed_paths.append(temp_file.name)
        
        return processed_paths
    except Exception as e:
        logger.error(f"Enhancement failed: {e}", exc_info=True)
        return [image_path]

async def process_static_image(image_path: str) -> list:
    """Process static images with multiple enhancements"""
    try:
        # Upscale small images
        with Image.open(image_path) as img:
            if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                scale_factor = max(MIN_WIDTH/img.width, MIN_HEIGHT/img.height)
                new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                img = img.resize(new_size, Image.LANCZOS)
                
                with NamedTemporaryFile(delete=False, suffix="_upscaled.jpg") as temp_file:
                    img.save(temp_file.name, "JPEG", quality=95)
                    image_path = temp_file.name
        
        return enhance_and_zoom(image_path)
    except Exception as e:
        logger.error(f"Static image processing failed: {e}", exc_info=True)
        return [image_path]

async def extract_video_frames(video_path: str) -> list:
    """Extract and enhance video frames with focus on details"""
    try:
        # Get video duration
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        
        # Extract strategic frames (start, middle, end)
        timestamps = [0.1, duration/2, duration-0.2]
        frames = []
        
        for i, ts in enumerate(timestamps):
            with NamedTemporaryFile(delete=False, suffix=f"_frame{i}.jpg") as frame_file:
                (
                    ffmpeg.input(video_path, ss=ts)
                    .filter('scale', 'iw*1.5', 'ih*1.5')  # Upscale
                    .output(frame_file.name, vframes=1, qscale=2)
                    .run(quiet=True, overwrite_output=True)
                )
                frames.extend(enhance_and_zoom(frame_file.name))
        
        return frames
    except Exception as e:
        logger.error(f"Video processing failed: {e}", exc_info=True)
        return []
    finally:
        os.remove(video_path)

async def process_media(message: Message, bot) -> list:
    """Process media with enhanced detail detection"""
    try:
        # Photos
        if message.photo:
            file_id = message.photo[-1].file_id
            path = await download_media(bot, file_id)
            return await process_static_image(path) if path else []
        
        # Stickers
        if message.sticker:
            sticker = message.sticker
            
            # Static sticker
            if not sticker.is_animated and not sticker.is_video:
                webp_path = await download_media(bot, sticker.file_id, "webp")
                if not webp_path: return []
                
                with Image.open(webp_path) as img:
                    with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                        img.convert("RGB").save(jpg_file.name, "JPEG", quality=95)
                        os.remove(webp_path)
                        return await process_static_image(jpg_file.name)
            
            # Video sticker
            elif sticker.is_video:
                webm_path = await download_media(bot, sticker.file_id, "webm")
                return await extract_video_frames(webm_path) if webm_path else []
            
            # Animated sticker
            elif sticker.is_animated:
                tgs_path = await download_media(bot, sticker.file_id, "tgs")
                if not tgs_path: return []
                
                with NamedTemporaryFile(delete=False, suffix=".png") as png_file:
                    os.system(f"lottie_convert.py {tgs_path} {png_file.name}")
                    os.remove(tgs_path)
                    
                    with Image.open(png_file.name) as img:
                        with NamedTemporaryFile(delete=False, suffix=".jpg") as jpg_file:
                            img.convert("RGB").save(jpg_file.name, "JPEG", quality=95)
                            os.remove(png_file.name)
                            return await process_static_image(jpg_file.name)
        
        return []
    except Exception as e:
        logger.error(f"Media processing failed: {e}", exc_info=True)
        return []
