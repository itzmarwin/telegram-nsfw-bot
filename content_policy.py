import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ContentPolicy:
    def __init__(self):
        self.nudity_threshold = 0.75
        self.child_abuse_zero_tolerance = True
        self.violence_zero_tolerance = True
        
        # Load from environment variables
        self.load_from_env()
        
    def load_from_env(self):
        try:
            nudity_threshold = os.getenv("NUDITY_THRESHOLD")
            if nudity_threshold:
                self.nudity_threshold = float(nudity_threshold)
                
            child_abuse = os.getenv("CHILD_ABUSE_ZERO_TOLERANCE")
            if child_abuse:
                self.child_abuse_zero_tolerance = child_abuse.lower() == "true"
                
            violence = os.getenv("VIOLENCE_ZERO_TOLERANCE")
            if violence:
                self.violence_zero_tolerance = violence.lower() == "true"
                
        except Exception as e:
            logger.error(f"Error loading policy settings: {e}")
    
    def should_delete(self, content_result: dict) -> bool:
        # Always delete child abuse content
        if self.child_abuse_zero_tolerance and content_result.get("child_abuse", False):
            return True
            
        # Always delete violent content
        if self.violence_zero_tolerance and content_result.get("violence", False):
            return True
            
        # Delete nudity above threshold
        if content_result.get("nudity", 0) >= self.nudity_threshold:
            return True
            
        return False

# Global policy instance
policy = ContentPolicy()
