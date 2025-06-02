import logging
import os
import time
import asyncio
import re
import cv2
import numpy as np
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector with aggressive settings
detector = NudeDetector(provider="gpu" if os.getenv("USE_GPU") == "true" else "cpu")

# Comprehensive prohibited patterns with hentai-specific terms
PROHIBITED_PATTERNS = {
    "explicit": [
        r"exposed_genitalia", r"genitalia", r"breast", r"anus", 
        r"penis", r"vagina", r"pussy", r"clitoris", r"buttocks", r"ass",
        r"intercourse", r"sex", r"bdsm", r"fetish", r"insertion", r"oral",
        r"pubic_hair", r"naked", r"nude", r"exposed_breast", r"exposed_anus",
        r"dick", r"cock", r"balls", r"tits", r"boobs", r"nipples", r"hentai",
        r"porn", r"cum", r"ejaculation", r"erection", r"blowjob", r"handjob",
        r"masturbation", r"orgasm", r"sex_toy", r"dildo", r"vibrator"
    ],
    "partial_nudity": [
        r"covered_genitalia", r"covered_breast", r"lingerie", r"underwear",
        r"bikini", r"cleavage", r"cameltoe", r"bulge", r"seductive", 
        r"provocative", r"suggestive", r"partial_nudity", r"see_through",
        r"wet_clothing", r"undressing", r"close_up_genitalia", r"thong",
        r"g-string", r"bra", r"panties", r"half_naked", r"half_nude",
        r"side_boob", r"underboob", r"areola", r"crotch", r"butt_crack"
    ],
    "child_abuse": [
        r"child", r"minor", r"teen", r"underage", r"loli", r"shota", 
        r"school", r"youth", r"adolescent", r"toddler", r"infant",
        r"juvenile", r"young_girl", r"young_boy", r"childlike"
    ],
    "violence": [
        r"gun", r"knife", r"weapon", r"blood", r"gore", r"torture", 
        r"abuse", r"hit", r"fight", r"injury", r"wound", r"brutality",
        r"assault", r"murder", r"suicide", r"self_harm"
    ]
}

def enhance_hentai_detection(image_path: str):
    """Specialized enhancement for hentai/partial nudity"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Increase saturation for anime colors
        h, s, v = cv2.split(hsv)
        s = cv2.add(s, 50)
        s = np.clip(s, 0, 255)
        hsv = cv2.merge([h, s, v])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Apply anime-style edge enhancement
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        enhanced = cv2.addWeighted(enhanced, 0.8, edges, 0.2, 0)
        
        # Save enhanced image
        cv2.imwrite(image_path, enhanced)
        return True
    except Exception as e:
        logger.error(f"Hentai enhancement failed: {e}")
        return False

def detect_skin_ratio(image_path: str) -> float:
    """Calculate skin pixel ratio for partial nudity detection"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return 0.0
            
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define skin color range (tuned for anime)
        lower_skin = np.array([0, 30, 60], dtype=np.uint8)
        upper_skin = np.array([20, 150, 255], dtype=np.uint8)
        
        # Create skin mask
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Calculate skin percentage
        skin_pixels = cv2.countNonZero(mask)
        total_pixels = img.shape[0] * img.shape[1]
        return skin_pixels / total_pixels
    except Exception as e:
        logger.error(f"Skin detection failed: {e}")
        return 0.0

async def classify_content(image_paths: list) -> dict:
    """Advanced classification with hentai/partial nudity focus"""
    if not image_paths:
        return {
            "max_explicit": 0,
            "max_partial_nudity": 0,
            "max_child_abuse": 0,
            "max_violence": 0,
            "skin_ratio": 0,
            "error": "No images provided"
        }
    
    results = []
    for path in image_paths:
        try:
            # Apply hentai-specific enhancement
            enhance_hentai_detection(path)
            
            start_time = time.time()
            
            # Run detection
            loop = asyncio.get_running_loop()
            detections = await loop.run_in_executor(
                None, 
                lambda: detector.detect(path)
            )
            
            # Calculate skin ratio for partial nudity
            skin_ratio = detect_skin_ratio(path)
            
            # Calculate scores based on patterns
            scores = {
                "explicit": 0.0,
                "partial_nudity": skin_ratio * 0.5,  # Start with skin ratio
                "child_abuse": 0.0,
                "violence": 0.0
            }
            
            detected_objects = {}
            
            for obj in detections:
                class_name = obj['class']
                confidence = obj['score']
                
                # Track all detected objects
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
            
            # Special handling for partial nudity
            if scores["explicit"] > 0.1 or "hentai" in path.lower():
                scores["partial_nudity"] = min(scores["partial_nudity"] * 1.5, 1.0)
            
            # Boost scores for stickers
            if "sticker" in path.lower():
                for category in scores:
                    scores[category] = min(scores[category] * 1.4, 1.0)
            
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
            "skin_ratio": 0,
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
