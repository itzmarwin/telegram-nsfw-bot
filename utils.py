import time
import datetime
import logging

logger = logging.getLogger(__name__)

def format_uptime(seconds):
    """Convert seconds to human-readable format"""
    time_delta = datetime.timedelta(seconds=seconds)
    days = time_delta.days
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} days")
    if hours > 0:
        parts.append(f"{hours} hours")
    if minutes > 0:
        parts.append(f"{minutes} minutes")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} seconds")
        
    return ", ".join(parts)

def is_owner(user_id: int) -> bool:
    """Check if user is the owner"""
    # OWNER_ID should be set in environment
    return user_id == int(os.getenv("OWNER_ID", 0))
