from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from datetime import datetime
import json

class Database:
    def __init__(self, mongodb_uri, database_name):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        
    def get_user_by_email(self, email):
        return self.db.users.find_one({"email": email})
    
    def get_user_by_id(self, user_id):
        return self.db.users.find_one({"_id": ObjectId(user_id)})
    
    def create_user(self, name, email, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = {
            "name": name,
            "email": email,
            "password": hashed_password.decode("utf-8"),  # ✅ Store as string
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        result = self.users.insert_one(user)
        return result.inserted_id

    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify the user's password using bcrypt.
        The hashed_password from MongoDB is stored as a string, so convert it to bytes.
        """
        # Convert stored hash to bytes
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")

        return bcrypt.checkpw(password.encode("utf-8"), hashed_password)

    
    def get_user_data_for_rag(self, user_id):
        """Get all user-related data for RAG processing"""
        user_object_id = ObjectId(user_id)
        
        # Get user info
        user = self.db.users.find_one({"_id": user_object_id})
        
        # Get user's locations
        locations = list(self.db.currentlocations.find({"userId": user_object_id}))
        
        # Get soil moisture data
        soil_data = list(self.db.soilmoisturetasks.find({"user": user_object_id}))
        
        # Get weather data
        weather_data = list(self.db.weathers.find({"userId": user_object_id}))
        
        # Get vegetation analysis
        vegetation_data = list(self.db.vegetationanalyses.find({"userId": user_object_id}))
        
        return {
            "user": user,
            "locations": locations,
            "soil_moisture": soil_data,
            "weather": weather_data,
            "vegetation": vegetation_data
        }
    
    def save_chat_message(self, user_id, message, response, message_type="user"):
        """Save chat conversation to database"""
        chat_data = {
            "userId": ObjectId(user_id),
            "message": message,
            "response": response,
            "messageType": message_type,
            "timestamp": datetime.utcnow()
        }
        return self.db.chat_history.insert_one(chat_data)
    
    def get_chat_history(self, user_id, limit=10):
        """Get recent chat history for a user"""
        return list(self.db.chat_history.find(
            {"userId": ObjectId(user_id)}
        ).sort("timestamp", -1).limit(limit))

class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB objects"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)