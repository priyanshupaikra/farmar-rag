from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from datetime import datetime
import json
from collections import defaultdict
import uuid

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
        result = self.db.users.insert_one(user)
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
    
    def save_chat_message(self, user_id, message, response, message_type="user", session_id=None):
        """Save chat conversation to database with session tracking"""
        chat_data = {
            "userId": ObjectId(user_id),
            "sessionId": session_id or str(uuid.uuid4()),
            "message": message,
            "response": response,
            "messageType": message_type,
            "timestamp": datetime.utcnow()
        }
        result = self.db.chat_history.insert_one(chat_data)
        return result.inserted_id, chat_data['sessionId']
    
    def get_chat_history(self, user_id, session_id=None, limit=50):
        """Get chat history for a user, optionally filtered by session"""
        query = {"userId": ObjectId(user_id)}
        if session_id:
            query["sessionId"] = session_id
            
        chat_history = list(self.db.chat_history.find(
            query
        ).sort("timestamp", 1).limit(limit))
        
        # Serialize the data to make it JSON serializable
        serialized_history = []
        for chat in chat_history:
            serialized_chat = chat.copy()
            # Convert ObjectId to string
            serialized_chat['_id'] = str(chat['_id'])
            serialized_chat['userId'] = str(chat['userId'])
            # Convert datetime to ISO format string
            serialized_chat['timestamp'] = chat['timestamp'].isoformat()
            serialized_history.append(serialized_chat)
            
        return serialized_history
    
    def get_chat_sessions(self, user_id):
        """Get distinct chat sessions for a user"""
        pipeline = [
            {"$match": {"userId": ObjectId(user_id)}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$sessionId",
                "title": {"$first": "$message"},
                "timestamp": {"$first": "$timestamp"},
                "message_count": {"$sum": 1}
            }},
            {"$sort": {"timestamp": -1}},
            {"$limit": 50}
        ]
        
        sessions = list(self.db.chat_history.aggregate(pipeline))
        
        # Format sessions for frontend and serialize data
        formatted_sessions = []
        for session in sessions:
            # Convert ObjectId to string
            session_id = str(session['_id'])
            # Convert datetime to ISO format string
            timestamp = session['timestamp']
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            # Truncate title to first 30 characters
            title = session['title'][:30] + "..." if len(session['title']) > 30 else session['title']
            formatted_sessions.append({
                'id': session_id,
                'title': title if title else "New Chat",
                'timestamp': timestamp,
                'message_count': session['message_count']
            })
        
        return formatted_sessions
    
    def create_new_chat_session(self, user_id):
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        return session_id
    
    def clear_chat_history(self, user_id, session_id=None):
        """Clear chat history for a user, optionally for a specific session"""
        query = {"userId": ObjectId(user_id)}
        if session_id:
            query["sessionId"] = session_id
        return self.db.chat_history.delete_many(query)

class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB objects"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)