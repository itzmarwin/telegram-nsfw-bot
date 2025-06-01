import logging
import time
import asyncio
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector (thread-safe)
detector = NudeDetector()

# Prohibited content categories
PROHIBITED_CATEGORIES = {
    "nudity": [
        "FEMALE_GENITALIA_EXPOSED",
        "MALE_GENITALIA_EXPOSED",
        "FEMALE_BREAST_EXPOSED",
        "ANUS_EXPOSED",
        "FEET_EXPOSED",
        "BELLY_EXPOSED",
        "ARMPITS_EXPOSED"
    ],
    "child_abuse": [
        "FEMALE_GENITALIA_COVERED",
        "MALE_GENITALIA_COVERED",
        "FEMALE_BREAST_COVERED",
        "ANUS_COVERED",
        "FEET_COVERED",
        "BELLY_COVERED",
        "ARMPITS_COVERED"
    ],
    "violence": [
        "GUN",
        "KNIFE",
        "BLOOD",
        "VIOLENCE"
    ]
}

async def classify_content(image_path: str) -> dict:
    """Classify media and detect prohibited objects"""
    try:
        start_time = time.time()
        
        # Run detection (async)
        loop = asyncio.get_running_loop()
        detections = await loop.run_in_executor(
            None, 
            lambda: detector.detect(image_path)
        )
        
        # Extract detected classes with their confidence scores
        detected_objects = {}
        for obj in detections:
            class_name = obj['class']
            confidence = obj['score']
            # Keep the highest confidence per class
            if class_name not in detected_objects or confidence > detected_objects[class_name]:
                detected_objects[class_name] = confidence
        
        # Calculate nudity score (max of nudity categories)
        nudity_score = 0.0
        for category in PROHIBITED_CATEGORIES["nudity"]:
            if category in detected_objects:
                nudity_score = max(nudity_score, detected_objects[category])
        
        # Check for child abuse content
        child_abuse_detected = any(
            category in detected_objects
            for category in PROHIBITED_CATEGORIES["child_abuse"]
        )
        
        # Check for violence
        violence_detected = any(
            category in detected_objects
            for category in PROHIBITED_CATEGORIES["violence"]
        )
        
        # Determine content type based on file path
        content_type = "image"
        if "sticker" in image_path.lower():
            content_type = "sticker"
        elif "frame" in image_path.lower():
            content_type = "video_frame"
        
        # Prepare results
        results = {
            "nudity": nudity_score,
            "child_abuse": child_abuse_detected,
            "violence": violence_detected,
            "content_type": content_type,
            "processing_time": time.time() - start_time,
            "detected_objects": list(detected_objects.keys())  # For debugging
        }
        
        logger.debug(f"Classification results: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Content classification failed: {e}", exc_info=True)
        return {
            "nudity": 0,
            "child_abuse": False,
            "violence": False,
            "content_type": "error",
            "error": str(e),
            "detected_objects": []
        }
