import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
        
    def connect(self):
        try:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            self.client = MongoClient(mongo_uri)
            self.db = self.client["nsfw_bot"]
            # Test connection
            self.db.command('ping')
            logger.info("✅ Connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.client = None
            self.db = None
    
    def is_connected(self):
        return self.client is not None
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        if not self.db:
            return False
        
        users = self.db.users
        user_data = {
            "_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "is_bot": False,
            "start_count": 1
        }
        
        try:
            users.update_one(
                {"_id": user_id},
                {"$set": user_data, "$inc": {"start_count": 1}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add user: {e}")
            return False
    
    def add_group(self, chat_id: int, title: str):
        if not self.db:
            return False
        
        groups = self.db.groups
        group_data = {
            "_id": chat_id,
            "title": title,
            "bot_added": True
        }
        
        try:
            groups.update_one(
                {"_id": chat_id},
                {"$set": group_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add group: {e}")
            return False
    
    def get_stats(self):
        if not self.db:
            return {}
        
        try:
            user_count = self.db.users.count_documents({})
            group_count = self.db.groups.count_documents({"bot_added": True})
            return {
                "users": user_count,
                "groups": group_count
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"users": 0, "groups": 0}
    
    def add_sudo(self, user_id: int):
        if not self.db:
            return False
        
        try:
            self.db.sudo_users.update_one(
                {"_id": user_id},
                {"$set": {"_id": user_id}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add sudo: {e}")
            return False
    
    def remove_sudo(self, user_id: int):
        if not self.db:
            return False
        
        try:
            result = self.db.sudo_users.delete_one({"_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove sudo: {e}")
            return False
    
    def get_sudo_list(self):
        if not self.db:
            return []
        
        try:
            return [doc["_id"] for doc in self.db.sudo_users.find({})]
        except Exception as e:
            logger.error(f"Failed to get sudo list: {e}")
            return []
    
    def is_sudo(self, user_id: int):
        if not self.db:
            return False
        
        try:
            return self.db.sudo_users.find_one({"_id": user_id}) is not None
        except Exception as e:
            logger.error(f"Failed to check sudo: {e}")
            return False

# Global database instance
db = Database()
