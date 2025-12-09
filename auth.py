from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# =====================================================
# SIGNUP ROUTE
# =====================================================
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        # Check if fields are empty
        if not username or not email or not password or not confirm_password:
            errors.append('All fields are required')
        
        # Check username length
        if username and len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        
        if username and len(username) > 50:
            errors.append('Username must be less than 50 characters')
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_pattern, email):
            errors.append('Invalid email format')
        
        # Check password length
        if password and len(password) < 6:
            errors.append('Password must be at least 6 characters long')
        
        # Check passwords match
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('auth.signup'))
        
        # Check if username already exists
        query = "SELECT user_id FROM USER WHERE username = %s"
        result = db.execute_query(query, (username,))
        if result:
            flash('Username already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        # Check if email already exists
        query = "SELECT user_id FROM USER WHERE email = %s"
        result = db.execute_query(query, (email,))
        if result:
            flash('Email already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Insert user into database
        query = "INSERT INTO USER (username, email, password_hash, status) VALUES (%s, %s, %s, %s)"
        rows_affected = db.execute_update(query, (username, email, password_hash, 'offline'))
        
        if rows_affected:
            user_id = db.get_insert_id()
            session['user_id'] = user_id
            session['username'] = username
            flash('Registration successful! Welcome to Messaging App', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Registration failed. Please try again', 'error')
            return redirect(url_for('auth.signup'))
    
    return render_template('signup.html')


# =====================================================
# LOGIN ROUTE
# =====================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        # Validation
        if not username_or_email or not password:
            flash('Username/Email and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        # Query user by username or email
        query = "SELECT user_id, username, email, password_hash FROM USER WHERE username = %s OR email = %s"
        result = db.execute_query(query, (username_or_email, username_or_email))
        
        if not result:
            flash('Invalid username/email or password', 'error')
            return redirect(url_for('auth.login'))
        
        user = result[0]
        
        # Check password
        if not check_password_hash(user['password_hash'], password):
            flash('Invalid username/email or password', 'error')
            return redirect(url_for('auth.login'))
        
        # Update user status to online
        query = "UPDATE USER SET status = %s, last_active = NOW() WHERE user_id = %s"
        db.execute_update(query, ('online', user['user_id']))
        
        # Create session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['email'] = user['email']
        
        flash(f'Welcome back, {user["username"]}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')


# =====================================================
# LOGOUT ROUTE
# =====================================================
@auth_bp.route('/logout')
def logout():
    # Update user status to offline
    if 'user_id' in session:
        user_id = session['user_id']
        query = "UPDATE USER SET status = %s WHERE user_id = %s"
        db.execute_update(query, ('offline', user_id))
    
    # Clear session
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))


# =====================================================
# CHECK IF USER IS LOGGED IN (Middleware)
# =====================================================
def login_required(f):
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    
    return decorated_function