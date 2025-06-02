import os
import logging
import re
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ContentPolicy:
    def __init__(self):
        # Aggressive default thresholds
        self.explicit_threshold = 0.42
        self.suggestive_threshold = 0.60
        self.child_abuse_threshold = 0.30
        self.violence_threshold = 0.45
        
        # Load from environment
        self.load_from_env()
        logger.info(f"Loaded thresholds: Explicit={self.explicit_threshold}, "
                   f"Suggestive={self.suggestive_threshold}, "
                   f"Child Abuse={self.child_abuse_threshold}, "
                   f"Violence={self.violence_threshold}")
    
    def load_from_env(self):
        try:
            # Load thresholds from environment with fallbacks
            self.explicit_threshold = float(os.getenv("EXPLICIT_THRESHOLD", "0.42"))
            self.suggestive_threshold = float(os.getenv("SUGGESTIVE_THRESHOLD", "0.60"))
            self.child_abuse_threshold = float(os.getenv("CHILD_ABUSE_THRESHOLD", "0.30"))
            self.violence_threshold = float(os.getenv("VIOLENCE_THRESHOLD", "0.45"))
        except Exception as e:
            logger.error(f"Config error: {e}")
    
    def should_delete(self, content_result: dict) -> bool:
        """Aggressive policy for subtle content"""
        if "error" in content_result:
            return False
            
        # 1. Explicit content detection (pussy, genitals, etc.)
        if content_result["max_explicit"] >= self.explicit_threshold:
            logger.warning(f"Explicit content detected: {content_result['max_explicit']:.2f} >= {self.explicit_threshold}")
            return True
        
        # 2. Suggestive content (covered genitals, bulges, cameltoe)
        if content_result["max_suggestive"] >= self.suggestive_threshold:
            logger.warning(f"Suggestive content detected: {content_result['max_suggestive']:.2f} >= {self.suggestive_threshold}")
            return True
        
        # 3. Child abuse zero tolerance
        if content_result["max_child_abuse"] >= self.child_abuse_threshold:
            logger.warning(f"Child abuse content detected: {content_result['max_child_abuse']:.2f} >= {self.child_abuse_threshold}")
            return True
        
        # 4. Violence detection
        if content_result["max_violence"] >= self.violence_threshold:
            logger.warning(f"Violent content detected: {content_result['max_violence']:.2f} >= {self.violence_threshold}")
            return True
        
        # 5. Composite detection for subtle content
        composite_score = (
            content_result["max_explicit"] * 0.8 +   # Higher weight for explicit
            content_result["max_suggestive"] * 0.6 +
            content_result["max_child_abuse"] * 1.0   # Highest weight for child abuse
        )
        
        # 6. Special handling for zoomed content
        if "zoom" in str(content_result.get("details", [])) and composite_score > 0.65:
            logger.warning(f"Subtle content detected via zoom: {composite_score:.2f}")
            return True
        
        # 7. Final composite check
        if composite_score > 0.75:
            logger.warning(f"Composite detection: {composite_score:.2f}")
            return True
        
        return False

# Global policy instance
policy = ContentPolicy()
