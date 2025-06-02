import logging
import time
import asyncio
import re
from nudenet import NudeDetector

logger = logging.getLogger(__name__)

detector = NudeDetector()

# Comprehensive prohibited patterns
PROHIBITED_PATTERNS = {
    "explicit": [
        r"exposed_genitalia", r"genitalia", r"breast", r"anus", 
        r"penis", r"vagina", r"pussy", r"clitoris", r"buttocks",
        r"intercourse", r"sex", r"bdsm", r"fetish", r"insertion"
    ],
    "suggestive": [
        r"covered_genitalia", r"covered_breast", r"lingerie",
        r"bikini", r"underwear", r"cleavage", r"cameltoe",
        r"bulge", r"seductive", r"provocative"
    ],
    "child_abuse": [
        r"child", r"minor", r"teen", r"underage", r"loli", 
        r"shota", r"school", r"youth", r"adolescent"
    ],
    "violence": [
        r"gun", r"knife", r"weapon", r"blood", r"gore",
        r"torture", r"abuse", r"hit", r"fight", r"injury"
    ]
}

async def classify_content(image_paths: list) -> dict:
    """Advanced classification with focus on subtle details"""
    if not image_paths:
        return {"error": "No images provided", "max_score": 0}
    
    results = []
    for path in image_paths:
        try:
            start_time = time.time()
            detections = await asyncio.get_running_loop().run_in_executor(
                None, detector.detect, path
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
            
            # Boost scores for suggestive content near explicit
            if scores["suggestive"] > 0.4 and scores["explicit"] > 0.2:
                scores["explicit"] = max(scores["explicit"], scores["suggestive"] * 1.2)
            
            # Penalize small images
            if "sticker" in path.lower() or "frame" in path.lower():
                for category in scores:
                    scores[category] *= 1.3  # Boost detection for stickers
                    
            results.append({
                "scores": scores,
                "detected_objects": detected_objects,
                "processing_time": time.time() - start_time,
                "image_path": path
            })
        except Exception as e:
            logger.error(f"Classification failed for {path}: {e}", exc_info=True)
    
    if not results:
        return {"error": "All classifications failed", "max_score": 0}
    
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
    
    return final
