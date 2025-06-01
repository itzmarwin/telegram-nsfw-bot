import logging
import time
import asyncio
import os
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector
detector = NudeDetector()

# Correct prohibited content categories (updated for NudeNet v3.4.2)
PROHIBITED_CATEGORIES = {
    "nudity": [
        "FEMALE_GENITALIA_EXPOSED",
        "MALE_GENITALIA_EXPOSED",
        "FEMALE_BREAST_EXPOSED",
        "ANUS_EXPOSED",
        "BUTTOCKS_EXPOSED"
    ],
    "child_abuse": [
        "FEMALE_GENITALIA_COVERED",
        "MALE_GENITALIA_COVERED",
        "FEMALE_BREAST_COVERED",
        "MINORS"
    ],
    "violence": [
        "GUN",
        "KNIFE",
        "BLOOD",
        "WEAPON"
    ]
}

async def classify_content(image_path: str) -> dict:
    """Classify media and detect prohibited objects with enhanced detection"""
    try:
        start_time = time.time()
        
        # Run detection (async)
        loop = asyncio.get_running_loop()
        detections = await loop.run_in_executor(
            None, 
            lambda: detector.detect(image_path)
        )
        
        # Log raw detections for debugging
        logger.info(f"Raw detections for {os.path.basename(image_path)}: {detections}")
        
        # Initialize results
        nudity_score = 0.0
        child_abuse = False
        violence = False
        
        # Process each detection
        for detection in detections:
            class_name = detection['class']
            score = detection['score']
            
            # Nudity detection (track highest score)
            if class_name in PROHIBITED_CATEGORIES["nudity"]:
                if score > nudity_score:
                    nudity_score = score
            
            # Child abuse detection (any match with sufficient confidence)
            if class_name in PROHIBITED_CATEGORIES["child_abuse"]:
                if score > 0.3:  # 30% confidence threshold
                    child_abuse = True
                    
            # Violence detection (any match with sufficient confidence)
            if class_name in PROHIBITED_CATEGORIES["violence"]:
                if score > 0.4:  # 40% confidence threshold
                    violence = True
        
        # Determine content type
        content_type = "image"
        if "sticker" in image_path.lower():
            content_type = "sticker"
        elif "frame" in image_path.lower():
            content_type = "video_frame"
        
        # Prepare results
        results = {
            "nudity": nudity_score,
            "child_abuse": child_abuse,
            "violence": violence,
            "content_type": content_type,
            "processing_time": time.time() - start_time
        }
        
        logger.debug(f"Classification results: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Content classification failed: {e}")
        return {
            "nudity": 0,
            "child_abuse": False,
            "violence": False,
            "content_type": "error",
            "error": str(e)
        }
