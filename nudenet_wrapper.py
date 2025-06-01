import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

async def classify_nsfw(image_path: str) -> float:
    """
    Fallback NSFW detection using skin tone analysis
    Returns high probability if large skin areas detected
    """
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return 0.0
        
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define skin color range (adjust as needed)
        lower_skin = np.array([0, 48, 80], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Create skin mask
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Calculate skin percentage
        skin_pixels = cv2.countNonZero(mask)
        total_pixels = img.shape[0] * img.shape[1]
        ratio = skin_pixels / total_pixels
        
        # Heuristic scoring (tune thresholds)
        if ratio > 0.4:   # 40% skin coverage
            return 0.95
        elif ratio > 0.2: # 20% skin coverage
            return 0.7
        else:
            return 0.1
            
    except Exception as e:
        logger.error(f"Fallback detection failed: {e}")
        return 0.0
