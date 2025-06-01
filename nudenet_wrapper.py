import logging
import time
import asyncio
import re
import cv2
import numpy as np
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

def enhance_image_contrast(image_path: str):
    """Increase contrast for better detection of small stickers"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L-channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        
        # Merge channels and convert back to BGR
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        # Save enhanced image
        cv2.imwrite(image_path, enhanced)
        return True
    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        return False

async def classify_content(image_paths: list) -> dict:
    """Classify media with enhanced video sticker handling"""
    if not image_paths:
        return {
            "nudity": 0,
            "child_abuse": 0,
            "violence": 0,
            "drugs": 0,
            "content_type": "error",
            "detected_objects": {},
            "error": "No images provided"
        }
    
    # Process each image
    results = []
    for image_path in image_paths:
        try:
            # Enhance contrast for small stickers
            if "sticker" in image_path.lower():
                enhance_image_contrast(image_path)
            
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
            
            # Prepare frame result
            frame_result = {
                "nudity": category_scores["nudity"],
                "child_abuse": category_scores["child_abuse"],
                "violence": category_scores["violence"],
                "drugs": category_scores["drugs"],
                "content_type": content_type,
                "detected_objects": detected_objects,
                "processing_time": time.time() - start_time,
                "frame_path": image_path
            }
            
            logger.info(
                f"Frame classification: {image_path} - "
                f"Nudity: {frame_result['nudity']:.2f}, "
                f"Child Abuse: {frame_result['child_abuse']:.2f}, "
                f"Objects: {list(detected_objects.keys())}"
            )
            
            results.append(frame_result)
        except Exception as e:
            logger.error(f"Frame classification failed: {e}", exc_info=True)
    
    # Aggregate results across all frames
    if not results:
        return {
            "nudity": 0,
            "child_abuse": 0,
            "violence": 0,
            "drugs": 0,
            "content_type": "error",
            "detected_objects": {},
            "error": "All frames failed classification"
        }
    
    # Get maximum scores across all frames
    final_result = {
        "nudity": max(r["nudity"] for r in results),
        "child_abuse": max(r["child_abuse"] for r in results),
        "violence": max(r["violence"] for r in results),
        "drugs": max(r["drugs"] for r in results),
        "content_type": results[0]["content_type"],
        "detected_objects": {},
        "frame_results": results,
        "frame_count": len(results)
    }
    
    # Combine detected objects
    for res in results:
        for class_name, confidence in res["detected_objects"].items():
            if class_name not in final_result["detected_objects"] or confidence > final_result["detected_objects"][class_name]:
                final_result["detected_objects"][class_name] = confidence
    
    logger.info(
        f"Final classification: "
        f"Nudity: {final_result['nudity']:.2f}, "
        f"Child Abuse: {final_result['child_abuse']:.2f}, "
        f"Violence: {final_result['violence']:.2f}, "
        f"Frames: {len(results)}"
    )
    
    return final_result
