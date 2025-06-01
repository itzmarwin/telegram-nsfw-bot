import logging
import time
import asyncio
from nudenet import NudeDetector  # Changed import

logger = logging.getLogger(__name__)

# Initialize detector
detector = NudeDetector()

# Prohibited content categories
PROHIBITED_CATEGORIES = {
    "nudity": ["EXPOSED_GENITALIA_F", "EXPOSED_GENITALIA_M", "EXPOSED_BREAST_F"],
    "child_abuse": ["COVERED_GENITALIA_F", "COVERED_GENITALIA_M"],
    "violence": ["GUN", "KNIFE", "BLOOD"]
}

async def classify_content(image_path: str) -> dict:
    """Classify media and detect prohibited objects"""
    try:
        start_time = time.time()
        
        # Run detection (async)
        loop = asyncio.get_running_loop()
        detections = await loop.run_in_executor(
            None, 
            lambda: detector.detect(image_path)  # New detection method
        )
        
        # Extract detected classes
        detected_objects = [obj['class'] for obj in detections]
        
        # Calculate nudity score
        nudity_scores = [obj['score'] for obj in detections 
                        if obj['class'] in PROHIBITED_CATEGORIES["nudity"]]
        nudity_score = max(nudity_scores) if nudity_scores else 0.0
        
        # Determine content type
        content_type = "image"
        if "sticker" in image_path.lower():
            content_type = "sticker"
        elif "frame" in image_path.lower():
            content_type = "video_frame"
        
        # Prepare results
        results = {
            "nudity": nudity_score,
            "child_abuse": any(
                obj in PROHIBITED_CATEGORIES["child_abuse"] 
                for obj in detected_objects
            ),
            "violence": any(
                obj in PROHIBITED_CATEGORIES["violence"] 
                for obj in detected_objects
            ),
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
