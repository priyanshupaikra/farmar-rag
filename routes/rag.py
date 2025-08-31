from flask import Blueprint, request, render_template, session, jsonify, flash, redirect, url_for
from models.database import Database, MongoJSONEncoder
from config import Config
import google.generativeai as genai
import json
from datetime import datetime

rag_bp = Blueprint('rag', __name__)
db = Database(Config.MONGODB_URI, Config.DATABASE_NAME)

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@rag_bp.route('/dashboard')
@login_required
def dashboard():
    user_data = db.get_user_data_for_rag(session['user_id'])
    
    # Prepare summary statistics
    stats = {
        'locations_count': len(user_data['locations']),
        'soil_data_count': len(user_data['soil_moisture']),
        'weather_data_count': len(user_data['weather']),
        'vegetation_data_count': len(user_data['vegetation'])
    }
    
    # Get latest data for display
    latest_location = user_data['locations'][0] if user_data['locations'] else None
    latest_soil = user_data['soil_moisture'][0] if user_data['soil_moisture'] else None
    latest_weather = user_data['weather'][0] if user_data['weather'] else None
    latest_vegetation = user_data['vegetation'][0] if user_data['vegetation'] else None
    
    return render_template('dashboard.html', 
                         stats=stats,
                         latest_location=latest_location,
                         latest_soil=latest_soil,
                         latest_weather=latest_weather,
                         latest_vegetation=latest_vegetation)

@rag_bp.route('/chat')
@login_required
def chat():
    # Get recent chat history
    chat_history = db.get_chat_history(session['user_id'], limit=20)
    chat_history.reverse()  # Show oldest first
    return render_template('chat.html', chat_history=chat_history)

@rag_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get user's data for RAG context
        user_data = db.get_user_data_for_rag(session['user_id'])
        
        # Convert data to JSON string for context
        context_data = json.dumps(user_data, cls=MongoJSONEncoder, indent=2)
        
        # Create RAG prompt
        rag_prompt = f"""
        You are an intelligent agricultural assistant. You have access to the user's agricultural monitoring data.
        
        User's Data Context:
        {context_data}
        
        Current Date: 2025-08-31 10:43:27 UTC
        User: {session['user_name']} ({session['user_email']})
        
        Based on the above data, please answer the user's question comprehensively and provide actionable insights.
        If the question is about trends, comparisons, or recommendations, use the historical data to provide detailed analysis.
        
        User Question: {user_message}
        
        Please provide a helpful, detailed response based on the available data. If specific data is not available, mention that clearly.
        """
        
        # Generate response using Gemini
        response = model.generate_content(rag_prompt)
        ai_response = response.text
        
        # Save conversation to database
        db.save_chat_message(session['user_id'], user_message, ai_response, "conversation")
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Chat API Error: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500

@rag_bp.route('/api/user-data')
@login_required
def api_user_data():
    """API endpoint to get user's data in JSON format"""
    try:
        user_data = db.get_user_data_for_rag(session['user_id'])
        return jsonify(user_data, cls=MongoJSONEncoder)
    except Exception as e:
        return jsonify({'error': str(e)}), 500