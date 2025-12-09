from flask import Blueprint, jsonify, request, session
from database.db import db
from routes.auth import login_required

contacts_bp = Blueprint('contacts', __name__, url_prefix='/api/contacts')

# =====================================================
# SEARCH USERS (for adding contacts)
# =====================================================
@contacts_bp.route('/search', methods=['GET'])
@login_required
def search_users():
    """Search for users by username or email"""
    query = request.args.get('q', '').strip()
    current_user_id = session.get('user_id')
    
    if len(query) < 2:
        return jsonify({'results': []})
    
    # Search for users matching the query (exclude current user)
    search_query = """
        SELECT user_id, username, email 
        FROM USER 
        WHERE (username LIKE %s OR email LIKE %s) 
        AND user_id != %s
        LIMIT 20
    """
    search_pattern = f"%{query}%"
    users = db.execute_query(search_query, (search_pattern, search_pattern, current_user_id))
    
    if not users:
        return jsonify({'results': []})
    
    # Check which users are already contacts
    contact_query = """
        SELECT contact_user_id 
        FROM USERCONTACT 
        WHERE user_id = %s
    """
    contacts = db.execute_query(contact_query, (current_user_id,))
    contact_ids = {c['contact_user_id'] for c in contacts} if contacts else set()
    
    # Add is_contact flag to each user
    results = []
    for user in users:
        results.append({
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'is_contact': user['user_id'] in contact_ids
        })
    
    return jsonify({'results': results})


# =====================================================
# LIST ALL CONTACTS
# =====================================================
@contacts_bp.route('/list', methods=['GET'])
@login_required
def list_contacts():
    """Get all contacts for the current user"""
    current_user_id = session.get('user_id')
    
    # Get all contacts with their current status
    query = """
        SELECT u.user_id, u.username, u.email, u.status, u.last_active
        FROM USERCONTACT uc
        JOIN USER u ON uc.contact_user_id = u.user_id
        WHERE uc.user_id = %s
        ORDER BY u.username ASC
    """
    
    contacts = db.execute_query(query, (current_user_id,))
    
    if not contacts:
        return jsonify({'contacts': []})
    
    return jsonify({'contacts': contacts})


# =====================================================
# ADD CONTACT
# =====================================================
@contacts_bp.route('/add', methods=['POST'])
@login_required
def add_contact():
    """Add a new contact"""
    current_user_id = session.get('user_id')
    data = request.get_json()
    contact_user_id = data.get('contact_user_id')
    
    if not contact_user_id:
        return jsonify({'success': False, 'error': 'Contact user ID is required'}), 400
    
    # Check if user exists
    user_query = "SELECT user_id FROM USER WHERE user_id = %s"
    user = db.execute_query(user_query, (contact_user_id,))
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check if already a contact
    check_query = """
        SELECT * FROM USERCONTACT 
        WHERE user_id = %s AND contact_user_id = %s
    """
    existing = db.execute_query(check_query, (current_user_id, contact_user_id))
    
    if existing:
        return jsonify({'success': False, 'error': 'Already in contacts'}), 400
    
    # Check if user is blocked
    block_query = """
        SELECT * FROM USERBLOCK 
        WHERE (blocker_id = %s AND blocked_id = %s) 
        OR (blocker_id = %s AND blocked_id = %s)
    """
    blocked = db.execute_query(block_query, (current_user_id, contact_user_id, 
                                               contact_user_id, current_user_id))
    
    if blocked:
        return jsonify({'success': False, 'error': 'Cannot add this user'}), 403
    
    # Add contact
    insert_query = """
        INSERT INTO USERCONTACT (user_id, contact_user_id, added_at) 
        VALUES (%s, %s, NOW())
    """
    result = db.execute_update(insert_query, (current_user_id, contact_user_id))
    
    if result:
        return jsonify({'success': True, 'message': 'Contact added successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to add contact'}), 500


# =====================================================
# REMOVE CONTACT
# =====================================================
@contacts_bp.route('/remove/<int:contact_user_id>', methods=['DELETE'])
@login_required
def remove_contact(contact_user_id):
    """Remove a contact"""
    current_user_id = session.get('user_id')
    
    delete_query = """
        DELETE FROM USERCONTACT 
        WHERE user_id = %s AND contact_user_id = %s
    """
    result = db.execute_update(delete_query, (current_user_id, contact_user_id))
    
    if result:
        return jsonify({'success': True, 'message': 'Contact removed'})
    else:
        return jsonify({'success': False, 'error': 'Failed to remove contact'}), 500


# =====================================================
# BLOCK USER
# =====================================================
@contacts_bp.route('/block', methods=['POST'])
@login_required
def block_user():
    """Block a user"""
    current_user_id = session.get('user_id')
    data = request.get_json()
    blocked_user_id = data.get('blocked_user_id')
    
    if not blocked_user_id:
        return jsonify({'success': False, 'error': 'User ID is required'}), 400
    
    # Check if already blocked
    check_query = """
        SELECT * FROM USERBLOCK 
        WHERE blocker_id = %s AND blocked_id = %s
    """
    existing = db.execute_query(check_query, (current_user_id, blocked_user_id))
    
    if existing:
        return jsonify({'success': False, 'error': 'User already blocked'}), 400
    
    # Block the user
    insert_query = """
        INSERT INTO USERBLOCK (blocker_id, blocked_id, blocked_at) 
        VALUES (%s, %s, NOW())
    """
    result = db.execute_update(insert_query, (current_user_id, blocked_user_id))
    
    if not result:
        return jsonify({'success': False, 'error': 'Failed to block user'}), 500
    
    # Remove from contacts if they exist
    delete_query = """
        DELETE FROM USERCONTACT 
        WHERE user_id = %s AND contact_user_id = %s
    """
    db.execute_update(delete_query, (current_user_id, blocked_user_id))
    
    return jsonify({'success': True, 'message': 'User blocked successfully'})


# =====================================================
# UNBLOCK USER
# =====================================================
@contacts_bp.route('/unblock/<int:blocked_user_id>', methods=['DELETE'])
@login_required
def unblock_user(blocked_user_id):
    """Unblock a user"""
    current_user_id = session.get('user_id')
    
    delete_query = """
        DELETE FROM USERBLOCK 
        WHERE blocker_id = %s AND blocked_id = %s
    """
    result = db.execute_update(delete_query, (current_user_id, blocked_user_id))
    
    if result:
        return jsonify({'success': True, 'message': 'User unblocked'})
    else:
        return jsonify({'success': False, 'error': 'Failed to unblock user'}), 500


# =====================================================
# GET BLOCKED USERS LIST
# =====================================================
@contacts_bp.route('/blocked', methods=['GET'])
@login_required
def get_blocked_users():
    """Get list of blocked users"""
    current_user_id = session.get('user_id')
    
    query = """
        SELECT u.user_id, u.username, u.email, ub.blocked_at
        FROM USERBLOCK ub
        JOIN USER u ON ub.blocked_id = u.user_id
        WHERE ub.blocker_id = %s
        ORDER BY ub.blocked_at DESC
    """
    
    blocked_users = db.execute_query(query, (current_user_id,))
    
    if not blocked_users:
        return jsonify({'blocked_users': []})
    
    return jsonify({'blocked_users': blocked_users})