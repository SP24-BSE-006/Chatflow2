from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_socketio import SocketIO
from database.db import db
from routes.auth import auth_bp, login_required
from routes.contacts import contacts_bp
from routes.messages import messages_bp
from routes.groups import groups_bp  # ✅ ADD THIS IMPORT
from socketio_events import register_socketio_events
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Initialize Socket.IO with proper session handling
socketio = SocketIO(app, 
                    cors_allowed_origins="*", 
                    async_mode='threading',
                    logger=False, 
                    engineio_logger=False,
                    ping_timeout=60,
                    ping_interval=25)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(contacts_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(groups_bp)  # ✅ ADD THIS LINE

# Register Socket.IO events
register_socketio_events(socketio)

# DEBUG: Print all registered routes
print("\n=== REGISTERED ROUTES ===")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint}: {rule.rule}")
print("========================\n")


# DATABASE CONNECTION

@app.before_request
def before_request():
    """Ensure database connection is active"""
    pass  # Connection pool handles this automatically

# HOME/INDEX ROUTE
@app.route('/')
def index():
    """Redirect to login or dashboard based on session"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))


# DASHBOARD ROUTE (requires login)
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard - shows chats and contacts"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    return render_template('dashboard.html', user_id=user_id, username=username)


# ERROR HANDLERS
@app.errorhandler(404)
def not_found_error(error):
    # Return JSON for API requests, HTML for regular requests
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return "404 - Page Not Found", 404


@app.errorhandler(500)
def internal_error(error):
    # Return JSON for API requests, HTML for regular requests
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return "500 - Internal Server Error", 500

# APP CONTEXT AND SHUTDOWN

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection on app shutdown"""
    try:
        if db and db.connection and db.connection.is_connected():
            db.disconnect()
    except:
        pass

# RUN APP

if __name__ == '__main__':
    # Connect to database on startup
    db.connect()
    
    # Run Flask app with Socket.IO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)