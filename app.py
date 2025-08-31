from flask import Flask, session
from flask_session import Session
from config import Config
from routes.auth import auth_bp
from routes.rag import rag_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    Session(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(rag_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)