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
        # Default policy thresholds
        self.nudity_threshold = 0.65
        self.child_abuse_zero_tolerance = True
        self.violence_zero_tolerance = True
        self.min_confidence = 0.45  # Minimum confidence to consider detection valid
        
        # Prohibited object categories
        self.prohibited_objects = {
            "nudity": [
                "EXPOSED_GENITALIA_F", "EXPOSED_GENITALIA_M", 
                "FEMALE_BREAST_EXPOSED", "ANUS_EXPOSED",
                "FEMALE_BREAST_COVERED", "MALE_GENITALIA_COVERED"
            ],
            "child_abuse": [
                "CHILD", "MINOR", "YOUNG", 
                "FEMALE_GENITALIA_COVERED", "MALE_GENITALIA_COVERED",
                "FEMALE_BREAST_COVERED", "ANUS_COVERED"
            ],
            "violence": [
                "GUN", "KNIFE", "WEAPON", "BLOOD", "VIOLENCE",
                "FIGHT", "HIT", "INJURY"
            ],
            "drugs": [
                "DRUGS", "PILLS", "SYRINGE", "JOINT", "SMOKING"
            ]
        }
        
        # Load settings from environment
        self.load_from_env()
        
    def load_from_env(self):
        try:
            nudity_threshold = os.getenv("NUDITY_THRESHOLD")
            if nudity_threshold:
                self.nudity_threshold = float(nudity_threshold)
                logger.info(f"Loaded nudity threshold: {self.nudity_threshold}")
                
            child_abuse = os.getenv("CHILD_ABUSE_ZERO_TOLERANCE")
            if child_abuse:
                self.child_abuse_zero_tolerance = child_abuse.lower() == "true"
                logger.info(f"Child abuse zero tolerance: {self.child_abuse_zero_tolerance}")
                
            violence = os.getenv("VIOLENCE_ZERO_TOLERANCE")
            if violence:
                self.violence_zero_tolerance = violence.lower() == "true"
                logger.info(f"Violence zero tolerance: {self.violence_zero_tolerance}")
                
            min_confidence = os.getenv("MIN_CONFIDENCE")
            if min_confidence:
                self.min_confidence = float(min_confidence)
                logger.info(f"Minimum detection confidence: {self.min_confidence}")
                
        except Exception as e:
            logger.error(f"Error loading policy settings: {e}")
    
    def should_delete(self, content_result: dict) -> bool:
        """Determine if content should be deleted based on policy"""
        # Extract detected objects with confidence
        detected_objects = content_result.get("detected_objects", {})
        
        # 1. Always delete child abuse content (zero tolerance)
        if self.child_abuse_zero_tolerance:
            for obj in self.prohibited_objects["child_abuse"]:
                if obj in detected_objects and detected_objects[obj] >= self.min_confidence:
                    logger.warning(f"Deleting for child abuse: {obj} ({detected_objects[obj]:.2f})")
                    return True
        
        # 2. Always delete violent content (zero tolerance)
        if self.violence_zero_tolerance:
            for obj in self.prohibited_objects["violence"]:
                if obj in detected_objects and detected_objects[obj] >= self.min_confidence:
                    logger.warning(f"Deleting for violence: {obj} ({detected_objects[obj]:.2f})")
                    return True
        
        # 3. Delete nudity above threshold
        nudity_score = content_result.get("nudity", 0)
        if nudity_score >= self.nudity_threshold:
            logger.warning(f"Deleting for nudity: {nudity_score:.2f} >= {self.nudity_threshold}")
            return True
        
        # 4. Check for any high-confidence prohibited objects
        for category, objects in self.prohibited_objects.items():
            for obj in objects:
                if obj in detected_objects and detected_objects[obj] >= self.min_confidence:
                    logger.warning(f"Deleting for prohibited object: {obj} ({detected_objects[obj]:.2f})")
                    return True
        
        # 5. Additional safety checks
        # Check for high-risk combinations (e.g., covered genitalia + minor)
        if ("COVERED_GENITALIA" in detected_objects or "COVERED_BREAST" in detected_objects) and \
           ("CHILD" in detected_objects or "MINOR" in detected_objects):
            logger.warning("Deleting for high-risk combination: Covered genitalia/breast with child/minor")
            return True
        
        # Check for drug-related content
        for drug_obj in self.prohibited_objects["drugs"]:
            if drug_obj in detected_objects and detected_objects[drug_obj] >= self.min_confidence:
                logger.warning(f"Deleting for drugs: {drug_obj} ({detected_objects[drug_obj]:.2f})")
                return True
        
        return False

# Global policy instance
policy = ContentPolicy()
