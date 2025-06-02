import logging
import time
import asyncio
import re
import cv2
import numpy as np
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

# Initialize detector
detector = NudeDetector()

# Comprehensive prohibited patterns - UPDATED WITH SPECIFIC TERMS
PROHIBITED_PATTERNS = {
    "explicit": [
        r"exposed_genitalia", r"genitalia", r"breast", r"anus", 
        r"penis", r"vagina", r"pussy", r"clitoris", r"buttocks", r"ass",
        r"intercourse", r"sex", r"bdsm", r"fetish", r"insertion", r"oral",
        r"pubic_hair", r"naked", r"nude", r"exposed_breast", r"exposed_anus"
    ],
    "suggestive": [
        r"covered_genitalia", r"covered_breast", r"lingerie", r"underwear",
        r"bikini", r"cleavage", r"cameltoe", r"bulge", r"seductive", 
        r"provocative", r"suggestive", r"partial_nudity", r"see_through",
        r"wet_clothing", r"nipples", r"undressing", r"close_up_genitalia"
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

def enhance_image_for_detection(image_path: str):
    """Apply enhancements to make subtle details more visible"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to LAB color space for better contrast control
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L-channel for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # Merge enhanced L-channel with original A and B channels
        limg = cv2.merge((cl, a, b))
        
        # Convert back to BGR color space
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        # Apply sharpening filter
        kernel = np.array([[-1, -1, -1], 
                           [-1, 9, -1], 
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Save enhanced image
        cv2.imwrite(image_path, sharpened)
        return True
    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        return False

async def classify_content(image_paths: list) -> dict:
    """Advanced classification with focus on subtle details"""
    if not image_paths:
        return {
            "max_explicit": 0,
            "max_suggestive": 0,
            "max_child_abuse": 0,
            "max_violence": 0,
            "error": "No images provided"
        }
    
    results = []
    for path in image_paths:
        try:
            # Enhance image for better detection of subtle details
            enhance_image_for_detection(path)
            
            start_time = time.time()
            
            # Run detection
            loop = asyncio.get_running_loop()
            detections = await loop.run_in_executor(
                None, 
                lambda: detector.detect(path)
            )
            
            # Calculate scores based on patterns
            scores = {category: 0.0 for category in PROHIBITED_PATTERNS}
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
            
            # Special handling for zoomed images
            enhancement_type = "original"
            if "zoom" in path:
                enhancement_type = "zoom"
                # Boost scores for zoomed images
                for category in scores:
                    scores[category] = min(scores[category] * 1.3, 1.0)
            
            # Boost scores for suggestive content near explicit
            if scores["suggestive"] > 0.4 and scores["explicit"] > 0.2:
                scores["explicit"] = max(scores["explicit"], scores["suggestive"] * 1.2)
            
            # Penalize small images
            if "sticker" in path.lower() or "frame" in path.lower():
                for category in scores:
                    scores[category] = min(scores[category] * 1.2, 1.0)
            
            results.append({
                "scores": scores,
                "detected_objects": detected_objects,
                "processing_time": time.time() - start_time,
                "image_path": path,
                "enhancement": enhancement_type
            })
            
            logger.debug(f"Processed {path}: Explicit={scores['explicit']:.2f}, "
                         f"Suggestive={scores['suggestive']:.2f}, "
                         f"Child Abuse={scores['child_abuse']:.2f}")
        except Exception as e:
            logger.error(f"Classification failed for {path}: {e}", exc_info=True)
    
    if not results:
        return {
            "max_explicit": 0,
            "max_suggestive": 0,
            "max_child_abuse": 0,
            "max_violence": 0,
            "error": "All classifications failed"
        }
    
    # Aggregate results
    final = {
        "max_explicit": max(r["scores"]["explicit"] for r in results),
        "max_suggestive": max(r["scores"]["suggestive"] for r in results),
        "max_child_abuse": max(r["scores"]["child_abuse"] for r in results),
        "max_violence": max(r["scores"]["violence"] for r in results),
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
               f"Suggestive={final['max_suggestive']:.2f}, "
               f"Child Abuse={final['max_child_abuse']:.2f}, "
               f"Versions={final['processed_versions']}")
    
    return final
