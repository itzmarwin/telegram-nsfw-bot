import logging
import time
import asyncio
import re
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector (thread-safe)
detector = NudeDetector()

# Prohibited content patterns (using regex for better matching)
PROHIBITED_PATTERNS = {
    "nudity": [
        r"exposed", r"genitalia", r"breast", r"anus", 
        r"naked", r"nude", r"sex", r"porn", r"hentai",
        r"bdsm", r"fuck", r"penis", r"vagina", r"ass"
    ],
    "child_abuse": [
        r"child", r"minor", r"young", r"teen", r"underage", 
        r"loli", r"shota", r"school", r"kid", r"young",
        r"covered_genitalia", r"covered_breast"
    ],
    "violence": [
        r"gun", r"knife", r"weapon", r"blood", r"violence",
        r"fight", r"hit", r"injury", r"wound", r"blood",
        r"gore", r"torture", r"abuse"
    ],
    "drugs": [
        r"drug", r"pill", r"syringe", r"joint", r"smoking",
        r"cocaine", r"heroin", r"marijuana", r"inject"
    ]
}

async def classify_content(image_path: str) -> dict:
    """Classify media and detect prohibited objects with enhanced pattern matching"""
    try:
        start_time = time.time()
        
        # Run detection (async)
        loop = asyncio.get_running_loop()
        detections = await loop.run_in_executor(
            None, 
            lambda: detector.detect(image_path)
        )
        
        # Create a dictionary of detected objects with confidence scores
        detected_objects = {}
        for obj in detections:
            class_name = obj['class']
            confidence = obj['score']
            # Keep the highest confidence per class
            if class_name not in detected_objects or confidence > detected_objects[class_name]:
                detected_objects[class_name] = confidence
        
        # Calculate category scores using pattern matching
        category_scores = {
            "nudity": 0.0,
            "child_abuse": 0.0,
            "violence": 0.0,
            "drugs": 0.0
        }
        
        # Calculate max score for each category
        for class_name, confidence in detected_objects.items():
            class_lower = class_name.lower()
            for category, patterns in PROHIBITED_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, class_lower):
                        if confidence > category_scores[category]:
                            category_scores[category] = confidence
        
        # Determine content type
        content_type = "image"
        if "sticker" in image_path.lower():
            content_type = "sticker"
        elif "frame" in image_path.lower():
            content_type = "video_frame"
        
        # Prepare results
        results = {
            "nudity": category_scores["nudity"],
            "child_abuse": category_scores["child_abuse"],
            "violence": category_scores["violence"],
            "drugs": category_scores["drugs"],
            "content_type": content_type,
            "detected_objects": detected_objects,
            "processing_time": time.time() - start_time
        }
        
        logger.info(
            f"Classification: {image_path} - "
            f"Nudity: {results['nudity']:.2f}, "
            f"Child Abuse: {results['child_abuse']:.2f}, "
            f"Violence: {results['violence']:.2f}, "
            f"Objects: {list(detected_objects.keys())}"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Content classification failed: {e}", exc_info=True)
        return {
            "nudity": 0,
            "child_abuse": 0,
            "violence": 0,
            "drugs": 0,
            "content_type": "error",
            "detected_objects": {},
            "error": str(e)
        }
