import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ContentPolicy:
    def __init__(self):
        # Aggressive default thresholds
        self.explicit_threshold = 0.45
        self.suggestive_threshold = 0.65
        self.child_abuse_threshold = 0.35
        self.violence_threshold = 0.50
        
        # Load from environment
        self.load_from_env()
        logger.info(f"Loaded thresholds: Explicit={self.explicit_threshold}")
    
    def load_from_env(self):
        try:
            self.explicit_threshold = float(os.getenv("EXPLICIT_THRESHOLD", "0.45"))
            self.suggestive_threshold = float(os.getenv("SUGGESTIVE_THRESHOLD", "0.65"))
            self.child_abuse_threshold = float(os.getenv("CHILD_ABUSE_THRESHOLD", "0.35"))
            self.violence_threshold = float(os.getenv("VIOLENCE_THRESHOLD", "0.50"))
        except Exception as e:
            logger.error(f"Config error: {e}")
    
    def should_delete(self, content_result: dict) -> bool:
        """Aggressive policy for subtle content"""
        if "error" in content_result:
            return False
            
        # Explicit content detection
        if content_result["max_explicit"] >= self.explicit_threshold:
            logger.warning(f"Explicit content detected: {content_result['max_explicit']:.2f}")
            return True
        
        # Suggestive content with high confidence
        if content_result["max_suggestive"] >= self.suggestive_threshold:
            logger.warning(f"Suggestive content detected: {content_result['max_suggestive']:.2f}")
            return True
        
        # Child abuse zero tolerance
        if content_result["max_child_abuse"] >= self.child_abuse_threshold:
            logger.warning(f"Child abuse content detected: {content_result['max_child_abuse']:.2f}")
            return True
        
        # Violence detection
        if content_result["max_violence"] >= self.violence_threshold:
            logger.warning(f"Violent content detected: {content_result['max_violence']:.2f}")
            return True
        
        # Composite detection for subtle content
        composite_score = (
            content_result["max_explicit"] * 0.7 +
            content_result["max_suggestive"] * 0.5 +
            content_result["max_child_abuse"] * 0.9
        )
        if composite_score > 0.75:
            logger.warning(f"Composite detection: {composite_score:.2f}")
            return True
        
        return False

policy = ContentPolicy()
