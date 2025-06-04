import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ContentPolicy:
    def __init__(self):
        # Adjusted thresholds to reduce false positives
        self.explicit_threshold = 0.45
        self.partial_nudity_threshold = 0.50
        self.child_abuse_threshold = 0.25
        self.violence_threshold = 0.40
        self.skin_ratio_threshold = 0.35
        
        # Load from environment
        self.load_from_env()
        logger.info(f"Optimized thresholds: Explicit={self.explicit_threshold}, "
                   f"Partial Nudity={self.partial_nudity_threshold}, "
                   f"Skin Ratio={self.skin_ratio_threshold}")
    
    def load_from_env(self):
        try:
            # Load thresholds from environment
            self.explicit_threshold = float(os.getenv("EXPLICIT_THRESHOLD", "0.45"))
            self.partial_nudity_threshold = float(os.getenv("PARTIAL_NUDITY_THRESHOLD", "0.50"))
            self.child_abuse_threshold = float(os.getenv("CHILD_ABUSE_THRESHOLD", "0.25"))
            self.violence_threshold = float(os.getenv("VIOLENCE_THRESHOLD", "0.40"))
            self.skin_ratio_threshold = float(os.getenv("SKIN_RATIO_THRESHOLD", "0.35"))
        except Exception as e:
            logger.error(f"Config error: {e}")
    
    def should_delete(self, content_result: dict) -> bool:
        """Optimized policy with reduced false positives"""
        if "error" in content_result:
            return False
            
        # 1. Explicit content detection (higher threshold)
        if content_result["max_explicit"] >= self.explicit_threshold:
            logger.warning(f"Explicit content: {content_result['max_explicit']:.2f} >= {self.explicit_threshold}")
            return True
        
        # 2. Partial nudity requires explicit elements
        if (content_result["max_partial_nudity"] >= self.partial_nudity_threshold and
            content_result["max_explicit"] > 0.2):
            logger.warning(f"Partial nudity: {content_result['max_partial_nudity']:.2f} >= {self.partial_nudity_threshold}")
            return True
        
        # 3. High skin ratio requires partial nudity
        if (content_result["avg_skin_ratio"] >= self.skin_ratio_threshold and
            content_result["max_partial_nudity"] > 0.3):
            logger.warning(f"High skin ratio: {content_result['avg_skin_ratio']:.2f} >= {self.skin_ratio_threshold}")
            return True
        
        # 4. Child abuse zero tolerance
        if content_result["max_child_abuse"] >= self.child_abuse_threshold:
            logger.warning(f"Child abuse: {content_result['max_child_abuse']:.2f} >= {self.child_abuse_threshold}")
            return True
        
        # 5. Violence detection
        if content_result["max_violence"] >= self.violence_threshold:
            logger.warning(f"Violence: {content_result['max_violence']:.2f} >= {self.violence_threshold}")
            return True
        
        # 6. Adjusted composite detection
        hentai_score = (
            content_result["max_explicit"] * 0.5 +
            content_result["max_partial_nudity"] * 0.4 +
            min(content_result["avg_skin_ratio"], 0.5) * 0.3
        )
        if hentai_score > 0.70:
            logger.warning(f"Hentai composite: {hentai_score:.2f}")
            return True
        
        return False

# Global policy instance
policy = ContentPolicy()
