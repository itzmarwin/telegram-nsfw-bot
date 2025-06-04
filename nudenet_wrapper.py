import logging
import os
import time
import asyncio
import re
import cv2
import numpy as np
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector
detector = NudeDetector()

# Refined prohibited patterns
PROHIBITED_PATTERNS = {
    "explicit": [
        r"exposed_genitalia", r"genitalia", r"breast", 
        r"penis", r"vagina", r"buttocks", r"ass",
        r"intercourse", r"sex", r"bdsm", r"insertion",
        r"pubic_hair", r"exposed_breast", r"exposed_anus",
    ],
    "partial_nudity": [
        r"covered_genitalia", r"covered_breast", r"lingerie",
        r"bikini", r"cleavage", r"partial_nudity",
        r"see_through", r"underwear"
    ],
    "child_abuse": [
        r"child", r"minor", r"teen", r"underage", r"loli", r"shota", 
        r"school", r"youth", r"adolescent"
    ],
    "violence": [
        r"gun", r"knife", r"weapon", r"blood", r"gore", r"torture", 
        r"abuse", r"hit", r"fight", r"injury", r"wound", r"brutality"
    ]
}

def enhance_hentai_detection(image_path: str):
    """Optimized enhancement for detection"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Moderate saturation increase
        h, s, v = cv2.split(hsv)
        s = cv2.add(s, 30)
        s = np.clip(s, 0, 255)
        hsv = cv2.merge([h, s, v])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        cv2.imwrite(image_path, enhanced)
        return True
    except Exception as e:
        logger.error(f"Hentai enhancement failed: {e}")
        return False

def detect_skin_ratio(image_path: str) -> float:
    """More accurate skin detection"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return 0.0
            
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Narrower skin color range
        lower_skin = np.array([0, 40, 70], dtype=np.uint8)
        upper_skin = np.array([25, 180, 255], dtype=np.uint8)
        
        # Create skin mask
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Apply morphological operations to reduce noise
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Calculate skin percentage
        skin_pixels = cv2.countNonZero(mask)
        total_pixels = img.shape[0] * img.shape[1]
        return skin_pixels / total_pixels
    except Exception as e:
        logger.error(f"Skin detection failed: {e}")
        return 0.0

async def classify_content(image_paths: list) -> dict:
    """Optimized classification with reduced false positives"""
    if not image_paths:
        return {
            "max_explicit": 0,
            "max_partial_nudity": 0,
            "max_child_abuse": 0,
            "max_violence": 0,
            "avg_skin_ratio": 0,
            "error": "No images provided"
        }
    
    # Process only first 2 images to save time
    if len(image_paths) > 2:
        image_paths = image_paths[:2]
    
    results = []
    for path in image_paths:
        try:
            # Only enhance zoomed/frame images
            if "_zoom" in path or "_frame" in path:
                enhance_hentai_detection(path)
            
            start_time = time.time()
            
            # Run detection
            loop = asyncio.get_running_loop()
            detections = await loop.run_in_executor(
                None, 
                lambda: detector.detect(path)
            )
            
            # Calculate skin ratio
            skin_ratio = detect_skin_ratio(path)
            
            # Calculate scores
            scores = {
                "explicit": 0.0,
                "partial_nudity": skin_ratio * 0.3,  # Reduced weight
                "child_abuse": 0.0,
                "violence": 0.0
            }
            
            detected_objects = {}
            
            for obj in detections:
                class_name = obj['class']
                confidence = obj['score']
                
                # Track detected objects
                detected_objects[class_name] = max(
                    detected_objects.get(class_name, 0),
                    confidence
                )
                
                # Apply pattern matching
                class_lower = class_name.lower()
                for category, patterns in PROHIBITED_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, class_lower):
                            if confidence > scores[category]:
                                scores[category] = confidence
            
            # Remove sticker score boost
            # Special case for popular sticker types
            if "popular" in path.lower() or "meme" in path.lower():
                scores["partial_nudity"] *= 0.6
            
            results.append({
                "scores": scores,
                "detected_objects": detected_objects,
                "skin_ratio": skin_ratio,
                "processing_time": time.time() - start_time,
                "image_path": path
            })
            
            logger.debug(f"Processed {path}: Explicit={scores['explicit']:.2f}, "
                         f"Partial Nudity={scores['partial_nudity']:.2f}, "
                         f"Skin Ratio={skin_ratio:.2f}")
        except Exception as e:
            logger.error(f"Classification failed for {path}: {e}", exc_info=True)
    
    if not results:
        return {
            "max_explicit": 0,
            "max_partial_nudity": 0,
            "max_child_abuse": 0,
            "max_violence": 0,
            "avg_skin_ratio": 0,
            "error": "All classifications failed"
        }
    
    # Aggregate results
    final = {
        "max_explicit": max(r["scores"]["explicit"] for r in results),
        "max_partial_nudity": max(r["scores"]["partial_nudity"] for r in results),
        "max_child_abuse": max(r["scores"]["child_abuse"] for r in results),
        "max_violence": max(r["scores"]["violence"] for r in results),
        "avg_skin_ratio": sum(r["skin_ratio"] for r in results) / len(results),
        "all_objects": {},
        "processed_versions": len(results),
        "details": results
    }
    
    # Combine detected objects
    for r in results:
        for obj, conf in r["detected_objects"].items():
            if conf > final["all_objects"].get(obj, 0):
                final["all_objects"][obj] = conf
    
    logger.info(f"Classification result: "
               f"Explicit={final['max_explicit']:.2f}, "
               f"Partial Nudity={final['max_partial_nudity']:.2f}, "
               f"Skin Ratio={final['avg_skin_ratio']:.2f}, "
               f"Versions={final['processed_versions']}")
    
    return final
