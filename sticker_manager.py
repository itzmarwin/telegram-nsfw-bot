import logging
import pymongo
from datetime import datetime
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from media_processor import process_media
from nudenet_wrapper import classify_content

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, mongo_uri, db_name):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.sticker_collection = self.db["sticker_classifications"]
        self.nsfw_collection = self.db["nsfw_stickers"]
        
        # Create indexes
        self.sticker_collection.create_index([("file_unique_id", pymongo.ASCENDING)], unique=True)
        self.nsfw_collection.create_index([("file_unique_id", pymongo.ASCENDING)], unique=True)
        logger.info("💾 Sticker Manager initialized with MongoDB")

    def get_feature_vector(self, content_result):
        """Create a feature vector from classification results"""
        return {
            "explicit": content_result.get("max_explicit", 0),
            "partial_nudity": content_result.get("max_partial_nudity", 0),
            "child_abuse": content_result.get("max_child_abuse", 0),
            "violence": content_result.get("max_violence", 0),
            "skin_ratio": content_result.get("avg_skin_ratio", 0),
            "objects": list(content_result.get("all_objects", {}).keys())
        }

    async def analyze_sticker(self, sticker_msg, bot):
        """Analyze a sticker and return results"""
        media_files = []
        try:
            media_files = await process_media(sticker_msg, bot)
            if not media_files:
                return None, "❌ Failed to process sticker."
            
            # Classify content
            content_result = await classify_content(media_files)
            
            # Create feature vector
            feature_vector = self.get_feature_vector(content_result)
            
            # Format results
            result_text = (
                f"📊 Sticker Analysis Results:\n\n"
                f"• Explicit: {content_result['max_explicit']:.2f}\n"
                f"• Partial Nudity: {content_result['max_partial_nudity']:.2f}\n"
                f"• Child Abuse: {content_result['max_child_abuse']:.2f}\n"
                f"• Violence: {content_result['max_violence']:.2f}\n"
                f"• Skin Ratio: {content_result['avg_skin_ratio']:.2f}\n\n"
                f"Detected Objects: {', '.join(feature_vector['objects'][:10])}"
            )
            
            return result_text, feature_vector
        except Exception as e:
            logger.error(f"Sticker analysis failed: {e}", exc_info=True)
            return None, f"❌ Error analyzing sticker: {str(e)}"
        finally:
            # Cleanup temporary files
            for file_path in media_files:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Failed to clean up {file_path}: {e}")

    def store_sticker_analysis(self, sticker, feature_vector, user_id):
        """Store sticker analysis in database"""
        sticker_data = {
            "file_id": sticker.file_id,
            "file_unique_id": sticker.file_unique_id,
            "set_name": sticker.set_name if sticker.set_name else "N/A",
            "features": feature_vector,
            "analysis_date": datetime.utcnow(),
            "added_by": user_id,
            "status": "analyzed"
        }
        self.sticker_collection.insert_one(sticker_data)

    def add_to_nsfw(self, file_unique_id, user_id):
        """Add sticker to NSFW collection"""
        # Get sticker data
        sticker_data = self.sticker_collection.find_one({"file_unique_id": file_unique_id})
        if not sticker_data:
            return False
        
        # Add to NSFW collection
        nsfw_data = {
            "file_unique_id": file_unique_id,
            "features": sticker_data["features"],
            "added_by": user_id,
            "added_date": datetime.utcnow()
        }
        self.nsfw_collection.insert_one(nsfw_data)
        
        # Update status in sticker collection
        self.sticker_collection.update_one(
            {"file_unique_id": file_unique_id},
            {"$set": {"status": "nsfw"}}
        )
        return True

    def is_nsfw_sticker(self, file_unique_id):
        """Check if sticker is in NSFW database"""
        return self.nsfw_collection.find_one({"file_unique_id": file_unique_id}) is not None

    def create_action_buttons(self, file_unique_id):
        """Create action buttons for sticker analysis"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Add to NSFW", callback_data=f"add_nsfw_{file_unique_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
