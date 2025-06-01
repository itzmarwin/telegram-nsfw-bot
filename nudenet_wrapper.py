import os
import logging
import urllib.request
from nude import NudeClassifier  # <-- use this instead of nudenet.classifier

logger = logging.getLogger(__name__)
MODEL_URL = "https://github.com/notAI-tech/NudeNet/releases/download/v0/classifier_model.onnx"
MODEL_PATH = os.path.expanduser("~/.NudeNet/classifier_model.onnx")

classifier = None  # add this to define classifier

def download_model():
    """Download model directly from GitHub"""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    try:
        logger.info("Downloading model from GitHub...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        logger.info("Model downloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        return False

def initialize_classifier():
    global classifier
    if classifier is None:
        # Ensure model exists
        if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) == 0:
            if not download_model():
                return
        try:
            logger.info("Loading classifier...")
            classifier = NudeClassifier()
            logger.info("Classifier loaded")
        except Exception as e:
            logger.error(f"Classifier init failed: {e}")
            # Try reinstalling model
            if os.path.exists(MODEL_PATH):
                os.remove(MODEL_PATH)
            if download_model():
                classifier = NudeClassifier()

async def classify_nsfw(image_path: str) -> float:
    try:
        initialize_classifier()
        if not classifier:
            logger.error("Classifier unavailable")
            return 0.0
        if not os.path.exists(image_path):
            logger.error(f"Missing image: {image_path}")
            return 0.0
        results = classifier.classify(image_path)
        return results[image_path].get('unsafe', 0.0)
    except Exception as e:
        logger.error(f"Classification error: {e}")
        return 0.0
        
