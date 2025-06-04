import os
import logging
import asyncio
import aiofiles
import cv2
import numpy as np
from tempfile import NamedTemporaryFile
from PIL import Image, ImageEnhance, ImageOps
from telegram import Message
import ffmpeg

logger = logging.getLogger(__name__)

# Optimized processing parameters
MIN_WIDTH = 350
MIN_HEIGHT = 350
ZOOM_FACTOR = 2.0
ENHANCE_FACTOR = 2.0

async def download_media(bot, file_id: str, ext: str = "jpg") -> str:
    """Download media with timeout handling"""
    try:
        media_file = await bot.get_file(file_id)
        with NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
            await asyncio.wait_for(
                media_file.download_to_drive(temp_file.name),
                timeout=15  # Reduced timeout
            )
            return temp_file.name
    except asyncio.TimeoutError:
        logger.warning("Media download timed out")
        return None
    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        return None

def enhance_hentai_image(image_path: str):
    """Optimized enhancement for hentai content"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Optimized contrast enhancement
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        # Moderate saturation boost
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        s = cv2.add(s, 50)
        s = np.clip(s, 0, 255)
        hsv = cv2.merge((h, s, v))
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        cv2.imwrite(image_path, enhanced)
        return True
    except Exception as e:
        logger.error(f"Hentai enhancement failed: {e}")
        return False

async def process_sticker(sticker_path: str) -> list:
    """Optimized processing for stickers"""
    try:
        enhanced_paths = [sticker_path]
        
        with Image.open(sticker_path) as img:
            # Only create zoomed version
            with NamedTemporaryFile(delete=False, suffix="_zoom.jpg") as temp_file:
                width, height = img.size
                zoom_width = int(width / ZOOM_FACTOR)
                zoom_height = int(height / ZOOM_FACTOR)
                left = (width - zoom_width) // 2
                top = (height - zoom_height) // 2
                zoomed = img.crop((left, top, left + zoom_width, top + zoom_height))
                zoomed = zoomed.resize((width, height), Image.LANCZOS)
                zoomed.save(temp_file.name, "JPEG", quality=95)
                enhanced_paths.append(temp_file.name)
        
        # Apply enhancement only to zoomed version
        enhance_hentai_image(enhanced_paths[1])
        return enhanced_paths
    except Exception as e:
        logger.error(f"Sticker processing failed: {e}", exc_info=True)
        return [sticker_path]

async def extract_video_frames(video_path: str) -> list:
    """Optimized frame extraction"""
    try:
        # Get video duration
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])
        
        # Extract only key frames
        timestamps = [0.1, duration/2, duration-0.1]
        
        frames = []
        for i, ts in enumerate(timestamps):
            with NamedTemporaryFile(delete=False, suffix=f"_frame{i}.jpg") as frame_file:
                (
                    ffmpeg.input(video_path, ss=ts)
                    .filter('scale', 'iw*1.5', 'ih*1.5')
                    .output(frame_file.name, vframes=1, qscale=2)
                    .run(quiet=True, overwrite_output=True)
                )
                frames.append(frame_file.name)
        
        # Enhance each frame
        for frame in frames:
            enhance_hentai_image(frame)
        
        return frames
    except Exception as e:
        logger.error(f"Video processing failed: {e}", exc_info=True)
        return []
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)

async def process_media(message: Message, bot) -> list:
    """Optimized media processing"""
    try:
        # Skip small stickers
        if message.sticker and message.sticker.file_size < 10240:
            logger.info(f"Skipping small sticker: {message.sticker.file_id}")
            return []
        
        # Photos
        if message.photo:
            file_id = message.photo[-1].file_id
            path = await download_media(bot, file_id)
            return await process_sticker(path) if path else []
        
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
                        return await process_sticker(jpg_file.name)
            
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
                            return await process_sticker(jpg_file.name)
        
        return []
    except Exception as e:
        logger.error(f"Media processing failed: {e}", exc_info=True)
        return []
