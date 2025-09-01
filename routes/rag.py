

from flask import Blueprint, request, render_template, session, jsonify, flash, redirect, url_for
from models.database import Database, MongoJSONEncoder
from config import Config
import google.generativeai as genai
import json
from datetime import datetime
from bson import ObjectId
from collections import defaultdict
import functools

rag_bp = Blueprint('rag', __name__)
db = Database(Config.MONGODB_URI, Config.DATABASE_NAME)

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # For external API access, we'll use a simple API key authentication
        # In production, you might want to use JWT tokens or OAuth
        api_key = request.headers.get('X-API-Key')
        user_id = request.headers.get('X-User-ID')
        
        if not api_key or not user_id:
            return jsonify({'error': 'API key and User ID are required'}), 401
        
        # In a real implementation, you would validate the API key against a database
        # For now, we'll just check if the user exists
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'Invalid user ID'}), 401
            
        # Add user info to the request context
        request.user_id = user_id
        request.user_name = user.get('name', '')
        request.user_email = user.get('email', '')
        
        return f(*args, **kwargs)
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
    # Initialize session_id in session if not present
    if 'chat_session_id' not in session:
        session['chat_session_id'] = db.create_new_chat_session(session['user_id'])
    
    # Check if a specific session is requested
    requested_session_id = request.args.get('session_id')
    if requested_session_id:
        # Set the requested session as current
        session['chat_session_id'] = requested_session_id
        # Get chat history for the requested session
        chat_history = db.get_chat_history(session['user_id'], requested_session_id, limit=50)
    else:
        # Get chat history for current session
        chat_history = db.get_chat_history(session['user_id'], session['chat_session_id'], limit=50)
    
    # Get chat sessions for sidebar
    chat_sessions = db.get_chat_sessions(session['user_id'])
    
    # If no sessions exist, create a default one
    if not chat_sessions:
        chat_sessions = [{
            'id': session['chat_session_id'],
            'title': 'Current Chat',
            'timestamp': datetime.utcnow(),
            'message_count': 0
        }]
    
    return render_template('chat.html', 
                         chat_history=chat_history,
                         chat_sessions=chat_sessions)

@rag_bp.route('/chat/new', methods=['POST'])
@login_required
def new_chat():
    """Create a new chat session"""
    try:
        # Create a new session ID
        new_session_id = db.create_new_chat_session(session['user_id'])
        session['chat_session_id'] = new_session_id
        
        flash('Started a new chat session.', 'info')
    except Exception as e:
        print(f"Error creating new chat session: {str(e)}")
        flash('Error starting new chat session', 'error')
    
    return redirect(url_for('rag.chat'))

@rag_bp.route('/chat/delete', methods=['POST'])
@login_required
def delete_chat():
    """Delete all chat history for the current user"""
    try:
        db.clear_chat_history(session['user_id'])
        # Create a new session after clearing
        new_session_id = db.create_new_chat_session(session['user_id'])
        session['chat_session_id'] = new_session_id
        flash('Chat history deleted successfully.', 'success')
    except Exception as e:
        print(f"Error deleting chat history: {str(e)}")
        flash('Error deleting chat history', 'error')
    
    return redirect(url_for('rag.chat'))

@rag_bp.route('/chat/session/<session_id>')
@login_required
def load_chat_session(session_id):
    """Load a specific chat session"""
    try:
        session['chat_session_id'] = session_id
        flash('Chat session loaded.', 'info')
    except Exception as e:
        print(f"Error loading chat session: {str(e)}")
        flash('Error loading chat session', 'error')
    
    return redirect(url_for('rag.chat'))

@rag_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Ensure we have a session ID
        if 'chat_session_id' not in session:
            session['chat_session_id'] = db.create_new_chat_session(session['user_id'])
        
        # Get user's data for RAG context
        user_data = db.get_user_data_for_rag(session['user_id'])
        
        # Convert data to JSON string for context
        context_data = json.dumps(user_data, cls=MongoJSONEncoder, indent=2)
        
        # Create improved RAG prompt for structured responses with more precise guidance
        rag_prompt = f"""
        You are an intelligent agricultural assistant. You have access to the user's agricultural monitoring data.
        
        User's Data Context:
        {context_data}
        
        Current Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        User: {session['user_name']} ({session['user_email']})
        
        Based on the above data, please answer the user's question with structured, concise responses.
        
        Guidelines for your response:
        1. Keep answers precise and to the point - avoid unnecessary elaboration
        2. Use bullet points and numbered lists where appropriate
        3. Highlight key information with **bold** text
        4. Avoid long paragraphs - break information into digestible points
        5. Use clear section headers with ## when needed
        6. Provide actionable insights and specific recommendations
        7. If comparing data, use clear before/after or increase/decrease language
        8. If data is not available, clearly state that
        9. Keep responses under 200 words unless specifically asked for more detail
        10. Focus only on the user's specific question - don't provide unrelated information
        
        User Question: {user_message}
        
        Please provide a helpful, structured response based on the available data.
        """
        
        # Generate response using Gemini
        response = model.generate_content(rag_prompt)
        ai_response = response.text
        
        # Save conversation to database with session tracking
        db.save_chat_message(session['user_id'], user_message, ai_response, "conversation", session['chat_session_id'])
        
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

@rag_bp.route('/api/external/user-data')
@api_key_required
def api_external_user_data():
    """API endpoint for external applications to get user's data"""
    try:
        user_data = db.get_user_data_for_rag(request.user_id)
        return jsonify(user_data, cls=MongoJSONEncoder)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/chat/history')
@login_required
def api_chat_history():
    """API endpoint to get chat history for current session"""
    try:
        session_id = session.get('chat_session_id')
        chat_history = db.get_chat_history(session['user_id'], session_id, limit=50)
        response_data = {
            'success': True,
            'chat_history': chat_history
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/external/chat/history')
@api_key_required
def api_external_chat_history():
    """API endpoint for external applications to get chat history"""
    try:
        session_id = request.args.get('session_id')
        chat_history = db.get_chat_history(request.user_id, session_id, limit=50)
        response_data = {
            'success': True,
            'chat_history': chat_history,
            'session_id': session_id
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/chat/history/<session_id>')
@login_required
def api_chat_history_session(session_id):
    """API endpoint to get chat history for a specific session"""
    try:
        print(f"Loading chat history for user {session['user_id']} and session {session_id}")
        chat_history = db.get_chat_history(session['user_id'], session_id, limit=50)
        print(f"Found {len(chat_history)} messages")
        response_data = {
            'success': True,
            'chat_history': chat_history
        }
        return jsonify(response_data)
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/chat/sessions')
@login_required
def api_chat_sessions():
    """API endpoint to get chat sessions"""
    try:
        chat_sessions = db.get_chat_sessions(session['user_id'])
        response_data = {
            'success': True,
            'chat_sessions': chat_sessions
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/external/chat/sessions')
@api_key_required
def api_external_chat_sessions():
    """API endpoint for external applications to get chat sessions"""
    try:
        chat_sessions = db.get_chat_sessions(request.user_id)
        response_data = {
            'success': True,
            'chat_sessions': chat_sessions
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/chat/session/new', methods=['POST'])
@login_required
def api_new_chat_session():
    """API endpoint to create a new chat session"""
    try:
        new_session_id = db.create_new_chat_session(session['user_id'])
        session['chat_session_id'] = new_session_id
        return jsonify({
            'success': True,
            'session_id': new_session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/external/chat/session/new', methods=['POST'])
@api_key_required
def api_external_new_chat_session():
    """API endpoint for external applications to create a new chat session"""
    try:
        new_session_id = db.create_new_chat_session(request.user_id)
        return jsonify({
            'success': True,
            'session_id': new_session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_bp.route('/api/chat/delete', methods=['POST'])
@login_required
def api_delete_chat_history():
    """API endpoint to delete all chat history for the current user"""
    try:
        db.clear_chat_history(session['user_id'])
        # Create a new session after clearing
        new_session_id = db.create_new_chat_session(session['user_id'])
        session['chat_session_id'] = new_session_id
        return jsonify({
            'success': True,
            'message': 'Chat history deleted successfully.'
        })
    except Exception as e:
        print(f"Error deleting chat history: {str(e)}")
        return jsonify({'error': 'Error deleting chat history'}), 500

@rag_bp.route('/api/external/chat/delete', methods=['POST'])
@api_key_required
def api_external_delete_chat_history():
    """API endpoint for external applications to delete all chat history for the current user"""
    try:
        db.clear_chat_history(request.user_id)
        # Create a new session after clearing
        new_session_id = db.create_new_chat_session(request.user_id)
        return jsonify({
            'success': True,
            'message': 'Chat history deleted successfully.',
            'session_id': new_session_id
        })
    except Exception as e:
        print(f"Error deleting chat history: {str(e)}")
        return jsonify({'error': 'Error deleting chat history'}), 500

@rag_bp.route('/api/external/chat', methods=['POST'])
@api_key_required
def api_external_chat():
    """API endpoint for external applications (like Next.js) to communicate with the RAG system"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        user_id = request.user_id
        
        # Ensure we have a session ID
        if not session_id:
            session_id = db.create_new_chat_session(user_id)
        
        # Get user's data for RAG context
        user_data = db.get_user_data_for_rag(user_id)
        
        # Convert data to JSON string for context
        context_data = json.dumps(user_data, cls=MongoJSONEncoder, indent=2)
        
        # Create improved RAG prompt for structured responses with more precise guidance
        rag_prompt = f"""
        You are an intelligent agricultural assistant. You have access to the user's agricultural monitoring data.
        
        User's Data Context:
        {context_data}
        
        Current Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        User: {request.user_name} ({request.user_email})
        
        Based on the above data, please answer the user's question with structured, concise responses.
        
        Guidelines for your response:
        1. Keep answers precise and to the point - avoid unnecessary elaboration
        2. Use bullet points and numbered lists where appropriate
        3. Highlight key information with **bold** text
        4. Avoid long paragraphs - break information into digestible points
        5. Use clear section headers with ## when needed
        6. Provide actionable insights and specific recommendations
        7. If comparing data, use clear before/after or increase/decrease language
        8. If data is not available, clearly state that
        9. Keep responses under 200 words unless specifically asked for more detail
        10. Focus only on the user's specific question - don't provide unrelated information
        
        User Question: {user_message}
        
        Please provide a helpful, structured response based on the available data.
        """
        
        # Generate response using Gemini
        response = model.generate_content(rag_prompt)
        ai_response = response.text
        
        # Save conversation to database with session tracking
        db.save_chat_message(user_id, user_message, ai_response, "conversation", session_id)
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"External Chat API Error: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500