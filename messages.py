from flask import Blueprint, jsonify, request, session
from database.db import db
from routes.auth import login_required
from datetime import datetime
import traceback

messages_bp = Blueprint('messages', __name__, url_prefix='/api/messages')

# =====================================================
# GET CHAT HISTORY (UPDATED FOR CONVERSATIONS)
# =====================================================
@messages_bp.route('/history/<int:contact_id>', methods=['GET'])
@login_required
def get_chat_history(contact_id):
    """Get all messages between current user and a contact"""
    try:
        current_user_id = session.get('user_id')
        
        print(f"[DEBUG] Getting chat history between {current_user_id} and {contact_id}")
        
        # First, find the conversation between these users
        conv_query = """
            SELECT cp1.conversation_id
            FROM CONVERSATION_PARTICIPANT cp1
            JOIN CONVERSATION_PARTICIPANT cp2 ON cp1.conversation_id = cp2.conversation_id
            JOIN CONVERSATION c ON c.conv_id = cp1.conversation_id
            WHERE cp1.user_id = %s 
              AND cp2.user_id = %s
              AND c.type = 'direct'
            LIMIT 1
        """
        conv_result = db.execute_query(conv_query, (current_user_id, contact_id))
        
        if not conv_result:
            print(f"[DEBUG] No conversation exists yet between {current_user_id} and {contact_id}")
            return jsonify({'messages': []})
        
        conv_id = conv_result[0]['conversation_id']
        print(f"[DEBUG] Found conversation: {conv_id}")
        
        # Get messages from this conversation
        query = """
            SELECT m.msg_id, m.sender_id, m.receiver_id, m.content, 
                   m.timestamp, m.status, m.attachment_path, m.edited, m.deleted,
                   u.username as sender_username
            FROM MESSAGE m
            JOIN USER u ON m.sender_id = u.user_id
            WHERE m.conv_id = %s
            ORDER BY m.timestamp ASC
            LIMIT 100
        """
        
        messages = db.execute_query(query, (conv_id,))
        
        if not messages:
            return jsonify({'messages': []})
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'msg_id': msg['msg_id'],
                'sender_id': msg['sender_id'],
                'receiver_id': msg['receiver_id'],
                'content': msg['content'],
                'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                'status': msg['status'],
                'attachment_path': msg['attachment_path'],
                'sender_username': msg['sender_username'],
                'is_mine': msg['sender_id'] == current_user_id,
                'edited': msg.get('edited', False),
                'deleted': msg.get('deleted', False)
            })
        
        print(f"[DEBUG] Returning {len(formatted_messages)} messages")
        return jsonify({'messages': formatted_messages})
    
    except Exception as e:
        print(f"[ERROR] Exception in get_chat_history: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# SEND MESSAGE (UPDATED)
# =====================================================
@messages_bp.route('/send', methods=['POST'])
@login_required
def send_message():
    """Send a message to a contact"""
    try:
        current_user_id = session.get('user_id')
        data = request.get_json()
        
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()
        
        print(f"[DEBUG] Sending message from {current_user_id} to {receiver_id}")
        
        if not receiver_id or not content:
            return jsonify({'success': False, 'error': 'Receiver and content required'}), 400
        
        # Check if receiver exists
        user_query = "SELECT user_id FROM USER WHERE user_id = %s"
        user = db.execute_query(user_query, (receiver_id,))
        
        if not user:
            print(f"[ERROR] User {receiver_id} not found")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if blocked
        block_query = """
            SELECT * FROM USERBLOCK 
            WHERE (blocker_id = %s AND blocked_id = %s) 
            OR (blocker_id = %s AND blocked_id = %s)
        """
        blocked = db.execute_query(block_query, (current_user_id, receiver_id, 
                                                  receiver_id, current_user_id))
        
        if blocked:
            print(f"[ERROR] User {current_user_id} and {receiver_id} have blocking relationship")
            return jsonify({'success': False, 'error': 'Cannot send message'}), 403
        
        # Get or create conversation
        conv_query = """
            SELECT cp1.conversation_id
            FROM CONVERSATION_PARTICIPANT cp1
            JOIN CONVERSATION_PARTICIPANT cp2 ON cp1.conversation_id = cp2.conversation_id
            JOIN CONVERSATION c ON c.conv_id = cp1.conversation_id
            WHERE cp1.user_id = %s 
              AND cp2.user_id = %s
              AND c.type = 'direct'
            LIMIT 1
        """
        conv_result = db.execute_query(conv_query, (current_user_id, receiver_id))
        
        if conv_result:
            conv_id = conv_result[0]['conversation_id']
            print(f"[DEBUG] Using existing conversation: {conv_id}")
        else:
            # Create new conversation
            print(f"[DEBUG] Creating new conversation between {current_user_id} and {receiver_id}")
            create_conv_query = """
                INSERT INTO CONVERSATION (type, created_by)
                VALUES ('direct', %s)
            """
            result = db.execute_update(create_conv_query, (current_user_id,))
            
            if not result:
                print("[ERROR] Failed to create conversation")
                return jsonify({'success': False, 'error': 'Failed to create conversation'}), 500
            
            conv_id = db.get_insert_id()
            print(f"[DEBUG] Created conversation: {conv_id}")
            
            # Add both participants
            add_participants_query = """
                INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id)
                VALUES (%s, %s), (%s, %s)
            """
            db.execute_update(add_participants_query, (conv_id, current_user_id, conv_id, receiver_id))
            print(f"[DEBUG] Added participants to conversation {conv_id}")
        
        # Insert message
        insert_query = """
            INSERT INTO MESSAGE (sender_id, receiver_id, content, conv_id, timestamp, status, pinned) 
            VALUES (%s, %s, %s, %s, NOW(), 'sent', FALSE)
        """
        result = db.execute_update(insert_query, (current_user_id, receiver_id, content, conv_id))
        
        if not result:
            print("[ERROR] Failed to insert message")
            return jsonify({'success': False, 'error': 'Failed to send message'}), 500
        
        # Get the inserted message ID
        msg_id = db.get_insert_id()
        print(f"[DEBUG] Inserted message: {msg_id}")
        
        # Update conversation last_message_at
        update_conv_query = """
            UPDATE CONVERSATION 
            SET last_message_at = NOW()
            WHERE conv_id = %s
        """
        db.execute_update(update_conv_query, (conv_id,))
        
        # Get the full message details
        msg_query = """
            SELECT m.msg_id, m.sender_id, m.receiver_id, m.content, 
                   m.timestamp, m.status, m.attachment_path,
                   u.username as sender_username
            FROM MESSAGE m
            JOIN USER u ON m.sender_id = u.user_id
            WHERE m.msg_id = %s
        """
        message = db.execute_query(msg_query, (msg_id,))
        
        if message:
            msg = message[0]
            return jsonify({
                'success': True,
                'message': {
                    'msg_id': msg['msg_id'],
                    'sender_id': msg['sender_id'],
                    'receiver_id': msg['receiver_id'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                    'status': msg['status'],
                    'sender_username': msg['sender_username'],
                    'is_mine': True,
                    'conv_id': conv_id
                }
            })
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"[ERROR] Exception in send_message: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


# =====================================================
# MARK MESSAGES AS READ (UPDATED)
# =====================================================
@messages_bp.route('/mark-read/<int:contact_id>', methods=['POST'])
@login_required
def mark_messages_read(contact_id):
    """Mark all messages from a contact as read"""
    try:
        current_user_id = session.get('user_id')
        
        print(f"[DEBUG] Marking messages as read: user={current_user_id}, contact={contact_id}")
        
        # Find conversation
        conv_query = """
            SELECT cp1.conversation_id
            FROM CONVERSATION_PARTICIPANT cp1
            JOIN CONVERSATION_PARTICIPANT cp2 ON cp1.conversation_id = cp2.conversation_id
            JOIN CONVERSATION c ON c.conv_id = cp1.conversation_id
            WHERE cp1.user_id = %s 
              AND cp2.user_id = %s
              AND c.type = 'direct'
            LIMIT 1
        """
        conv_result = db.execute_query(conv_query, (current_user_id, contact_id))
        
        if not conv_result:
            return jsonify({'success': True, 'updated': 0})
        
        conv_id = conv_result[0]['conversation_id']
        
        # Mark messages as read
        update_query = """
            UPDATE MESSAGE 
            SET status = 'read' 
            WHERE conv_id = %s
            AND receiver_id = %s 
            AND status != 'read'
        """
        
        result = db.execute_update(update_query, (conv_id, current_user_id))
        
        print(f"[DEBUG] Marked {result} messages as read")
        return jsonify({'success': True, 'updated': result if result else 0})
    
    except Exception as e:
        print(f"[ERROR] Exception in mark_messages_read: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# DELETE MESSAGE
# =====================================================
@messages_bp.route('/delete/<int:msg_id>', methods=['DELETE'])
@login_required
def delete_message(msg_id):
    """Delete a message (only if sender) - Soft delete"""
    current_user_id = session.get('user_id')
    
    # Check if user owns the message
    check_query = "SELECT sender_id, receiver_id FROM MESSAGE WHERE msg_id = %s"
    message = db.execute_query(check_query, (msg_id,))
    
    if not message or message[0]['sender_id'] != current_user_id:
        return jsonify({'success': False, 'error': 'Cannot delete this message'}), 403
    
    receiver_id = message[0]['receiver_id']
    
    # Soft delete - mark as deleted instead of removing
    delete_query = """
        UPDATE MESSAGE 
        SET deleted = TRUE, deleted_at = NOW(), content = 'This message was deleted'
        WHERE msg_id = %s
    """
    result = db.execute_update(delete_query, (msg_id,))
    
    if result:
        return jsonify({'success': True, 'message': 'Message deleted', 'receiver_id': receiver_id, 'msg_id': msg_id})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete message'}), 500


# =====================================================
# EDIT MESSAGE
# =====================================================
@messages_bp.route('/edit/<int:msg_id>', methods=['PUT'])
@login_required
def edit_message(msg_id):
    """Edit a message (only if sender)"""
    current_user_id = session.get('user_id')
    data = request.get_json()
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({'success': False, 'error': 'Message content required'}), 400
    
    # Check if user owns the message
    check_query = "SELECT sender_id, receiver_id FROM MESSAGE WHERE msg_id = %s"
    message = db.execute_query(check_query, (msg_id,))
    
    if not message or message[0]['sender_id'] != current_user_id:
        return jsonify({'success': False, 'error': 'Cannot edit this message'}), 403
    
    receiver_id = message[0]['receiver_id']
    
    # Update the message content and mark as edited
    update_query = """
        UPDATE MESSAGE 
        SET content = %s, edited = TRUE, edited_at = NOW()
        WHERE msg_id = %s
    """
    result = db.execute_update(update_query, (new_content, msg_id))
    
    if result:
        return jsonify({
            'success': True, 
            'message': 'Message updated',
            'msg_id': msg_id,
            'content': new_content,
            'receiver_id': receiver_id
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to update message'}), 500


# =====================================================
# GET UNREAD COUNT
# =====================================================
@messages_bp.route('/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """Get unread message count for current user"""
    current_user_id = session.get('user_id')
    
    query = """
        SELECT COUNT(*) as unread_count
        FROM MESSAGE 
        WHERE receiver_id = %s AND status != 'read'
    """
    
    result = db.execute_query(query, (current_user_id,))
    
    if result:
        return jsonify({'unread_count': result[0]['unread_count']})
    
    return jsonify({'unread_count': 0})


# =====================================================
# GET UNREAD COUNT PER CONTACT
# =====================================================
@messages_bp.route('/unread-per-contact', methods=['GET'])
@login_required
def get_unread_per_contact():
    """Get unread message count for each contact"""
    current_user_id = session.get('user_id')
    
    query = """
        SELECT sender_id, COUNT(*) as unread_count
        FROM MESSAGE 
        WHERE receiver_id = %s AND status != 'read'
        GROUP BY sender_id
    """
    
    result = db.execute_query(query, (current_user_id,))
    
    if not result:
        return jsonify({'unread': {}})
    
    # Format as dictionary
    unread_dict = {row['sender_id']: row['unread_count'] for row in result}
    
    return jsonify({'unread': unread_dict})