from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify
from models.database import Database
from config import Config

auth_bp = Blueprint('auth', __name__)
db = Database(Config.MONGODB_URI, Config.DATABASE_NAME)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('rag.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        user = db.get_user_by_email(email)
        
        if user and db.verify_password(password, user['password']):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash('Login successful!', 'success')
            return redirect(url_for('rag.dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([name, email, password]):
            flash('All fields are required', 'error')
            return render_template('login.html')
        
        # Check if user already exists
        if db.get_user_by_email(email):
            flash('Email already registered', 'error')
            return render_template('login.html')
        
        try:
            user_id = db.create_user(name, email, password)
            session['user_id'] = str(user_id)
            session['user_name'] = name
            session['user_email'] = email
            flash('Registration successful!', 'success')
            return redirect(url_for('rag.dashboard'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))