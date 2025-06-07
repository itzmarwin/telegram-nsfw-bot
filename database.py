import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

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
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            self.client = None
            self.db = None
    
    def is_connected(self):
        return self.client is not None and self.db is not None
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        if self.db is None:
            logger.warning("Database not connected, skipping add_user")
            return False
        
        users = self.db.users
        
        try:
            # Check if user already exists
            existing_user = users.find_one({"_id": user_id})
            
            if existing_user:
                # Update existing user
                users.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "username": username,
                            "first_name": first_name,
                            "last_name": last_name
                        },
                        "$inc": {"start_count": 1}
                    }
                )
            else:
                # Create new user
                user_data = {
                    "_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_bot": False,
                    "start_count": 1
                }
                users.insert_one(user_data)
                
            logger.info(f"Added/updated user: {user_id} ({first_name} {last_name})")
            return True
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to add user: {e}")
            return False
    
    def add_group(self, chat_id: int, title: str):
        if self.db is None:
            logger.warning("Database not connected, skipping add_group")
            return False
        
        groups = self.db.groups
        
        try:
            # Check if group already exists
            existing_group = groups.find_one({"_id": chat_id})
            
            if existing_group:
                # Update existing group
                groups.update_one(
                    {"_id": chat_id},
                    {"$set": {"title": title}}
                )
            else:
                # Create new group
                group_data = {
                    "_id": chat_id,
                    "title": title,
                    "bot_added": True
                }
                groups.insert_one(group_data)
                
            logger.info(f"Added/updated group: {chat_id} ({title})")
            return True
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to add group: {e}")
            return False
    
    def get_stats(self):
        if self.db is None:
            logger.warning("Database not connected, returning empty stats")
            return {"users": 0, "groups": 0}
        
        try:
            user_count = self.db.users.count_documents({})
            group_count = self.db.groups.count_documents({"bot_added": True})
            logger.info(f"Stats: users={user_count}, groups={group_count}")
            return {
                "users": user_count,
                "groups": group_count
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"users": 0, "groups": 0}
    
    def get_all_user_ids(self):
        if self.db is None:
            return []
        try:
            return [user["_id"] for user in self.db.users.find({}, {"_id": 1})]
        except Exception as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []
    
    def get_all_group_ids(self):
        if self.db is None:
            return []
        try:
            return [group["_id"] for group in self.db.groups.find({"bot_added": True}, {"_id": 1})]
        except Exception as e:
            logger.error(f"Failed to get group IDs: {e}")
            return []
    
    def add_sudo(self, user_id: int, username: str, first_name: str, last_name: str):
        if self.db is None:
            logger.warning("Database not connected, skipping add_sudo")
            return False
        
        try:
            self.db.sudo_users.update_one(
                {"_id": user_id},
                {"$set": {
                    "_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name
                }},
                upsert=True
            )
            logger.info(f"Added sudo user: {user_id} ({first_name} {last_name})")
            return True
        except Exception as e:
            logger.error(f"Failed to add sudo: {e}")
            return False
    
    def remove_sudo(self, user_id: int):
        if self.db is None:
            logger.warning("Database not connected, skipping remove_sudo")
            return False
        
        try:
            result = self.db.sudo_users.delete_one({"_id": user_id})
            logger.info(f"Removed sudo user: {user_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove sudo: {e}")
            return False
    
    def get_sudo_list(self):
        if self.db is None:
            logger.warning("Database not connected, returning empty sudo list")
            return []
        
        try:
            return list(self.db.sudo_users.find({}))
        except Exception as e:
            logger.error(f"Failed to get sudo list: {e}")
            return []
    
    def is_sudo(self, user_id: int):
        if self.db is None:
            return False
        
        try:
            return self.db.sudo_users.find_one({"_id": user_id}) is not None
        except Exception as e:
            logger.error(f"Failed to check sudo: {e}")
            return False

# Global database instance
db = Database()
