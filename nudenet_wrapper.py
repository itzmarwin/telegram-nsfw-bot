import os
import logging
from nude import NudeClassifier  # Requires nude-net package

# Initialize classifier globally
classifier = None
logger = logging.getLogger(__name__)

def initialize_classifier():
    """Initialize NudeNet classifier once"""
    global classifier
    if classifier is None:
        logger.info("Loading NudeNet classifier...")
        classifier = NudeClassifier()
        logger.info("Classifier loaded successfully")

async def classify_nsfw(image_path: str) -> float:
    """
    Classify image as NSFW and return unsafe probability score
    Returns 0.0 if error occurs
    """
    try:
        initialize_classifier()
        
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return 0.0
        
        # Get classification results
        results = classifier.classify(image_path)
        unsafe_prob = results[image_path].get('unsafe', 0.0)
        
        logger.debug(f"Classification results for {image_path}: {results}")
        return unsafe_prob
        
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return 0.0
