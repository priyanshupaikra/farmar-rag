import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    MONGODB_URI = os.getenv('MONGODB_URI', "mongodb+srv://hellobhuwanthapa45_db_user:tqb3U4dsGCWLXYZx@cluster0.xfvhhfx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBWEMg7aJLuPBwb6j3T8oGP92D8XeQNY90')
    DATABASE_NAME = 'test'