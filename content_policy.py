import os
import logging
import re
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
        # Default policy thresholds
        self.nudity_threshold = 0.55
        self.child_abuse_threshold = 0.45
        self.violence_threshold = 0.50
        self.min_confidence = 0.40
        
        # Prohibited object categories with pattern matching
        self.prohibited_patterns = {
            "child_abuse": [
                r"child", r"minor", r"young", r"teen", r"underage", 
                r"loli", r"shota", r"school", r"kid", r"young",
                r"covered_genitalia", r"covered_breast"
            ],
            "violence": [
                r"gun", r"knife", r"weapon", r"blood", r"violence",
                r"fight", r"hit", r"injury", r"wound", r"blood",
                r"gore", r"torture", r"abuse"
            ],
            "nudity": [
                r"exposed", r"genitalia", r"breast", r"anus", 
                r"naked", r"nude", r"sex", r"porn", r"hentai",
                r"bdsm", r"fuck", r"penis", r"vagina", r"ass"
            ],
            "drugs": [
                r"drug", r"pill", r"syringe", r"joint", r"smoking",
                r"cocaine", r"heroin", r"marijuana", r"inject"
            ]
        }
        
        # Load settings from environment
        self.load_from_env()
        logger.info("Content policy initialized with settings:")
        logger.info(f"Nudity threshold: {self.nudity_threshold}")
        logger.info(f"Child abuse threshold: {self.child_abuse_threshold}")
        logger.info(f"Violence threshold: {self.violence_threshold}")
        logger.info(f"Min confidence: {self.min_confidence}")
        
    def load_from_env(self):
        try:
            self.nudity_threshold = float(os.getenv("NUDITY_THRESHOLD", "0.55"))
            self.child_abuse_threshold = float(os.getenv("CHILD_ABUSE_THRESHOLD", "0.45"))
            self.violence_threshold = float(os.getenv("VIOLENCE_THRESHOLD", "0.50"))
            self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.40"))
        except Exception as e:
            logger.error(f"Error loading policy settings: {e}")
    
    def contains_prohibited_pattern(self, class_name: str, confidence: float) -> bool:
        """Check if class name matches any prohibited pattern"""
        if confidence < self.min_confidence:
            return False
            
        class_name = class_name.lower()
        for category, patterns in self.prohibited_patterns.items():
            for pattern in patterns:
                if re.search(pattern, class_name):
                    return True
        return False
    
    def calculate_category_score(self, detected_objects: dict, category: str) -> float:
        """Calculate max score for a category"""
        max_score = 0.0
        for class_name, confidence in detected_objects.items():
            if confidence >= self.min_confidence:
                for pattern in self.prohibited_patterns[category]:
                    if re.search(pattern, class_name.lower()):
                        if confidence > max_score:
                            max_score = confidence
        return max_score
    
    def should_delete(self, content_result: dict) -> bool:
        """Determine if content should be deleted based on policy"""
        detected_objects = content_result.get("detected_objects", {})
        
        # Calculate category scores
        nudity_score = self.calculate_category_score(detected_objects, "nudity")
        child_abuse_score = self.calculate_category_score(detected_objects, "child_abuse")
        violence_score = self.calculate_category_score(detected_objects, "violence")
        
        # Log detection details
        logger.debug(
            f"Detection scores - Nudity: {nudity_score:.2f}, "
            f"Child Abuse: {child_abuse_score:.2f}, "
            f"Violence: {violence_score:.2f}"
        )
        
        # 1. Check nudity
        if nudity_score >= self.nudity_threshold:
            logger.warning(f"Deleting for nudity: {nudity_score:.2f} >= {self.nudity_threshold}")
            return True
        
        # 2. Check child abuse
        if child_abuse_score >= self.child_abuse_threshold:
            logger.warning(f"Deleting for child abuse: {child_abuse_score:.2f} >= {self.child_abuse_threshold}")
            return True
        
        # 3. Check violence
        if violence_score >= self.violence_threshold:
            logger.warning(f"Deleting for violence: {violence_score:.2f} >= {self.violence_threshold}")
            return True
        
        # 4. Check for any high-confidence prohibited objects
        for class_name, confidence in detected_objects.items():
            if confidence >= self.min_confidence and self.contains_prohibited_pattern(class_name, confidence):
                logger.warning(f"Deleting for prohibited object: {class_name} ({confidence:.2f})")
                return True
        
        # 5. Check for high-risk combinations
        if (child_abuse_score > 0.3 and nudity_score > 0.3) or \
           (violence_score > 0.4 and nudity_score > 0.3):
            logger.warning(f"Deleting for high-risk combination: "
                          f"CA: {child_abuse_score:.2f}, N: {nudity_score:.2f}, V: {violence_score:.2f}")
            return True
        
        return False

# Global policy instance
policy = ContentPolicy()
