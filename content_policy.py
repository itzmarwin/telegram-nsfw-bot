# In the should_delete method
def should_delete(self, content_result: dict) -> bool:
    # Always delete child abuse content
    if self.child_abuse_zero_tolerance and content_result.get("child_abuse", False):
        return True
        
    # Always delete violent content
    if self.violence_zero_tolerance and content_result.get("violence", False):
        return True
        
    # Lowered nudity threshold
    if content_result.get("nudity", 0) >= self.nudity_threshold:
        return True
        
    # Add additional checks
    if content_result.get("detected_objects"):
        # Delete if any prohibited object detected with high confidence
        prohibited = ["CHILD", "ABUSE", "VIOLENCE", "PORN"]
        if any(obj in prohibited for obj in content_result["detected_objects"]):
            return True
            
    return False
