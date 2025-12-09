from flask import Blueprint, jsonify, request, session
from database.db import db
from routes.auth import login_required
import traceback

groups_bp = Blueprint('groups', __name__, url_prefix='/api/groups')

# =====================================================
# CREATE GROUP
# =====================================================
@groups_bp.route('/create', methods=['POST'])
@login_required
def create_group():
    """Create a new group conversation"""
    try:
        current_user_id = session.get('user_id')
        data = request.get_json()
        
        group_name = data.get('name', '').strip()
        member_ids = data.get('members', [])  # List of user IDs
        privacy = data.get('privacy', 'private')
        
        if not group_name:
            return jsonify({'success': False, 'error': 'Group name required'}), 400
        
        if len(member_ids) < 1:
            return jsonify({'success': False, 'error': 'At least 1 member required'}), 400
        
        # Ensure current user is included
        if current_user_id not in member_ids:
            member_ids.append(current_user_id)
        
        # Create conversation
        create_query = """
            INSERT INTO CONVERSATION (type, name, created_by, privacy_settings)
            VALUES ('group', %s, %s, %s)
        """
        result = db.execute_update(create_query, (group_name, current_user_id, privacy))
        
        if not result:
            return jsonify({'success': False, 'error': 'Failed to create group'}), 500
        
        group_id = db.get_insert_id()
        
        # Add creator as admin
        add_creator_query = """
            INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role)
            VALUES (%s, %s, 'admin')
        """
        db.execute_update(add_creator_query, (group_id, current_user_id))
        
        # Add other members
        for member_id in member_ids:
            if member_id != current_user_id:
                add_member_query = """
                    INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role)
                    VALUES (%s, %s, 'member')
                """
                db.execute_update(add_member_query, (group_id, member_id))
        
        print(f"[DEBUG] Created group {group_id}: {group_name} with {len(member_ids)} members")
        
        return jsonify({
            'success': True,
            'group_id': group_id,
            'message': 'Group created successfully'
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in create_group: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# LIST USER'S GROUPS
# =====================================================
@groups_bp.route('/list', methods=['GET'])
@login_required
def list_groups():
    """Get all groups that user is a member of"""
    try:
        current_user_id = session.get('user_id')
        
        query = """
            SELECT c.conv_id, c.name, c.created_by, c.created_at, c.last_message_at,
                   c.privacy_settings,
                   cp.role,
                   (SELECT COUNT(*) FROM CONVERSATION_PARTICIPANT 
                    WHERE conversation_id = c.conv_id) as member_count,
                   (SELECT COUNT(*) FROM MESSAGE 
                    WHERE conv_id = c.conv_id AND receiver_id = %s AND status != 'read') as unread_count
            FROM CONVERSATION c
            JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
            WHERE c.type = 'group' AND cp.user_id = %s
            ORDER BY c.last_message_at DESC, c.created_at DESC
        """
        
        groups = db.execute_query(query, (current_user_id, current_user_id))
        
        if not groups:
            return jsonify({'groups': []})
        
        # Format groups for frontend
        formatted_groups = []
        for group in groups:
            formatted_groups.append({
                'group_id': group['conv_id'],
                'name': group['name'],
                'created_by': group['created_by'],
                'created_at': group['created_at'].isoformat() if group['created_at'] else None,
                'last_message_at': group['last_message_at'].isoformat() if group['last_message_at'] else None,
                'privacy': group['privacy_settings'],
                'role': group['role'],
                'member_count': group['member_count'],
                'unread_count': group['unread_count'] or 0
            })
        
        return jsonify({'groups': formatted_groups})
    
    except Exception as e:
        print(f"[ERROR] Exception in list_groups: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# GET GROUP DETAILS
# =====================================================
@groups_bp.route('/<int:group_id>', methods=['GET'])
@login_required
def get_group_details(group_id):
    """Get group information including members"""
    try:
        current_user_id = session.get('user_id')
        
        # Check if user is member
        member_check = """
            SELECT role FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        membership = db.execute_query(member_check, (group_id, current_user_id))
        
        if not membership:
            return jsonify({'success': False, 'error': 'Not a member of this group'}), 403
        
        # Get group info
        group_query = """
            SELECT c.conv_id, c.name, c.created_by, c.created_at, c.privacy_settings,
                   u.username as creator_username
            FROM CONVERSATION c
            JOIN USER u ON u.user_id = c.created_by
            WHERE c.conv_id = %s AND c.type = 'group'
        """
        group = db.execute_query(group_query, (group_id,))
        
        if not group:
            return jsonify({'success': False, 'error': 'Group not found'}), 404
        
        # Get members
        members_query = """
            SELECT u.user_id, u.username, u.email, u.status, cp.role, cp.joined_at
            FROM CONVERSATION_PARTICIPANT cp
            JOIN USER u ON u.user_id = cp.user_id
            WHERE cp.conversation_id = %s
            ORDER BY cp.role DESC, u.username ASC
        """
        members = db.execute_query(members_query, (group_id,))
        
        group_data = group[0]
        return jsonify({
            'success': True,
            'group': {
                'group_id': group_data['conv_id'],
                'name': group_data['name'],
                'created_by': group_data['created_by'],
                'creator_username': group_data['creator_username'],
                'created_at': group_data['created_at'].isoformat() if group_data['created_at'] else None,
                'privacy': group_data['privacy_settings'],
                'user_role': membership[0]['role'],
                'members': [{
                    'user_id': m['user_id'],
                    'username': m['username'],
                    'email': m['email'],
                    'status': m['status'],
                    'role': m['role'],
                    'joined_at': m['joined_at'].isoformat() if m['joined_at'] else None
                } for m in members]
            }
        })
    
    except Exception as e:
        print(f"[ERROR] Exception in get_group_details: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# GET GROUP MESSAGES
# =====================================================
@groups_bp.route('/<int:group_id>/messages', methods=['GET'])
@login_required
def get_group_messages(group_id):
    """Get all messages in a group"""
    try:
        current_user_id = session.get('user_id')
        
        # Check if user is member
        member_check = """
            SELECT 1 FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        membership = db.execute_query(member_check, (group_id, current_user_id))
        
        if not membership:
            return jsonify({'success': False, 'error': 'Not a member of this group'}), 403
        
        # Get messages
        query = """
            SELECT m.msg_id, m.sender_id, m.content, m.timestamp, 
                   m.status, m.attachment_path, m.edited, m.deleted,
                   u.username as sender_username
            FROM MESSAGE m
            JOIN USER u ON m.sender_id = u.user_id
            WHERE m.conv_id = %s
            ORDER BY m.timestamp ASC
            LIMIT 200
        """
        
        messages = db.execute_query(query, (group_id,))
        
        if not messages:
            return jsonify({'messages': []})
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'msg_id': msg['msg_id'],
                'sender_id': msg['sender_id'],
                'sender_username': msg['sender_username'],
                'content': msg['content'],
                'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                'status': msg['status'],
                'attachment_path': msg['attachment_path'],
                'is_mine': msg['sender_id'] == current_user_id,
                'edited': msg.get('edited', False),
                'deleted': msg.get('deleted', False)
            })
        
        return jsonify({'messages': formatted_messages})
    
    except Exception as e:
        print(f"[ERROR] Exception in get_group_messages: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# SEND GROUP MESSAGE
# =====================================================
@groups_bp.route('/<int:group_id>/send', methods=['POST'])
@login_required
def send_group_message(group_id):
    """Send a message to a group"""
    try:
        current_user_id = session.get('user_id')
        data = request.get_json()
        
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'error': 'Message content required'}), 400
        
        # Check if user is member
        member_check = """
            SELECT 1 FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        membership = db.execute_query(member_check, (group_id, current_user_id))
        
        if not membership:
            return jsonify({'success': False, 'error': 'Not a member of this group'}), 403
        
        # Insert message (receiver_id = sender_id for group messages)
        insert_query = """
            INSERT INTO MESSAGE (sender_id, receiver_id, content, conv_id, timestamp, status, pinned)
            VALUES (%s, %s, %s, %s, NOW(), 'sent', FALSE)
        """
        result = db.execute_update(insert_query, (current_user_id, current_user_id, content, group_id))
        
        if not result:
            return jsonify({'success': False, 'error': 'Failed to send message'}), 500
        
        msg_id = db.get_insert_id()
        
        # Update conversation last_message_at
        update_conv_query = """
            UPDATE CONVERSATION 
            SET last_message_at = NOW()
            WHERE conv_id = %s
        """
        db.execute_update(update_conv_query, (group_id,))
        
        # Get the message details
        msg_query = """
            SELECT m.msg_id, m.sender_id, m.content, m.timestamp, m.status,
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
                    'sender_username': msg['sender_username'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                    'status': msg['status'],
                    'is_mine': True,
                    'group_id': group_id
                }
            })
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"[ERROR] Exception in send_group_message: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# ADD MEMBER TO GROUP
# =====================================================
@groups_bp.route('/<int:group_id>/add-member', methods=['POST'])
@login_required
def add_member(group_id):
    """Add a member to group (admin only)"""
    try:
        current_user_id = session.get('user_id')
        data = request.get_json()
        
        new_member_id = data.get('user_id')
        
        if not new_member_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        # Check if current user is admin
        role_check = """
            SELECT role FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        user_role = db.execute_query(role_check, (group_id, current_user_id))
        
        if not user_role or user_role[0]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can add members'}), 403
        
        # Check if user already member
        member_check = """
            SELECT 1 FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        existing = db.execute_query(member_check, (group_id, new_member_id))
        
        if existing:
            return jsonify({'success': False, 'error': 'User already in group'}), 400
        
        # Add member
        add_query = """
            INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role)
            VALUES (%s, %s, 'member')
        """
        result = db.execute_update(add_query, (group_id, new_member_id))
        
        if result:
            return jsonify({'success': True, 'message': 'Member added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to add member'}), 500
    
    except Exception as e:
        print(f"[ERROR] Exception in add_member: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# REMOVE MEMBER FROM GROUP
# =====================================================
@groups_bp.route('/<int:group_id>/remove-member/<int:member_id>', methods=['DELETE'])
@login_required
def remove_member(group_id, member_id):
    """Remove a member from group (admin only)"""
    try:
        current_user_id = session.get('user_id')
        
        # Check if current user is admin
        role_check = """
            SELECT role FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        user_role = db.execute_query(role_check, (group_id, current_user_id))
        
        if not user_role or user_role[0]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can remove members'}), 403
        
        # Cannot remove creator
        creator_check = """
            SELECT created_by FROM CONVERSATION WHERE conv_id = %s
        """
        creator = db.execute_query(creator_check, (group_id,))
        
        if creator and creator[0]['created_by'] == member_id:
            return jsonify({'success': False, 'error': 'Cannot remove group creator'}), 400
        
        # Remove member
        delete_query = """
            DELETE FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        result = db.execute_update(delete_query, (group_id, member_id))
        
        if result:
            return jsonify({'success': True, 'message': 'Member removed'})
        else:
            return jsonify({'success': False, 'error': 'Failed to remove member'}), 500
    
    except Exception as e:
        print(f"[ERROR] Exception in remove_member: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# LEAVE GROUP
# =====================================================
@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    """Leave a group"""
    try:
        current_user_id = session.get('user_id')
        
        # Check if user is creator
        creator_check = """
            SELECT created_by FROM CONVERSATION WHERE conv_id = %s
        """
        creator = db.execute_query(creator_check, (group_id,))
        
        if creator and creator[0]['created_by'] == current_user_id:
            return jsonify({'success': False, 'error': 'Creator cannot leave. Delete group instead.'}), 400
        
        # Remove from group
        delete_query = """
            DELETE FROM CONVERSATION_PARTICIPANT
            WHERE conversation_id = %s AND user_id = %s
        """
        result = db.execute_update(delete_query, (group_id, current_user_id))
        
        if result:
            return jsonify({'success': True, 'message': 'Left group successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to leave group'}), 500
    
    except Exception as e:
        print(f"[ERROR] Exception in leave_group: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# DELETE GROUP
# =====================================================
@groups_bp.route('/<int:group_id>/delete', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """Delete a group (creator only)"""
    try:
        current_user_id = session.get('user_id')
        
        # Check if user is creator
        creator_check = """
            SELECT created_by FROM CONVERSATION WHERE conv_id = %s
        """
        creator = db.execute_query(creator_check, (group_id,))
        
        if not creator or creator[0]['created_by'] != current_user_id:
            return jsonify({'success': False, 'error': 'Only creator can delete group'}), 403
        
        # Delete group (cascade will delete participants and messages)
        delete_query = """
            DELETE FROM CONVERSATION WHERE conv_id = %s
        """
        result = db.execute_update(delete_query, (group_id,))
        
        if result:
            return jsonify({'success': True, 'message': 'Group deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete group'}), 500
    
    except Exception as e:
        print(f"[ERROR] Exception in delete_group: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500