from flask_socketio import emit, join_room, leave_room
from flask import request
from database.db import db

# Store online users: {user_id: socket_id}
online_users = {}

def register_socketio_events(socketio):
    """Register all Socket.IO event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle user connection"""
        user_id = request.args.get('user_id')
        
        if user_id:
            user_id = int(user_id)
            online_users[user_id] = request.sid
            
            # Update user status to online
            try:
                query = "UPDATE USER SET status = 'online', last_active = NOW() WHERE user_id = %s"
                db.execute_update(query, (user_id,))
            except Exception as e:
                print(f"✗ Error updating user status: {e}")
            
            # Join personal room
            join_room(f'user_{user_id}')
            
            # Join all group rooms that user is member of
            try:
                group_query = """
                    SELECT conversation_id FROM CONVERSATION_PARTICIPANT
                    WHERE user_id = %s
                """
                groups = db.execute_query(group_query, (user_id,))
                if groups:
                    for group in groups:
                        join_room(f'group_{group["conversation_id"]}')
                        print(f"✓ User {user_id} joined group room {group['conversation_id']}")
            except Exception as e:
                print(f"✗ Error joining group rooms: {e}")
            
            # Notify contacts that user is online
            emit('user_online', {'user_id': user_id}, broadcast=True)
            
            print(f"✓ User {user_id} connected - Online users: {len(online_users)}")
            return {'status': 'connected', 'user_id': user_id}
        else:
            print("✗ Connection rejected - No user_id")
            return False
    
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle user disconnection"""
        user_id = None
        for uid, sid in online_users.items():
            if sid == request.sid:
                user_id = uid
                break
        
        if user_id:
            online_users.pop(user_id, None)
            
            # Update user status to offline
            try:
                query = "UPDATE USER SET status = 'offline', last_active = NOW() WHERE user_id = %s"
                db.execute_update(query, (user_id,))
            except Exception as e:
                print(f"✗ Error updating user status: {e}")
            
            # Leave personal room
            leave_room(f'user_{user_id}')
            
            # Notify contacts that user is offline
            emit('user_offline', {'user_id': user_id}, broadcast=True)
            
            print(f"✓ User {user_id} disconnected - Online users: {len(online_users)}")
    
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle real-time message sending - Direct messages only"""
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()
        
        print(f"📨 Received message: sender={sender_id}, receiver={receiver_id}, content={content}")
        
        if not receiver_id or not content or not sender_id:
            emit('message_error', {'error': 'Missing data'})
            return
        
        try:
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
            conv_result = db.execute_query(conv_query, (sender_id, receiver_id))
            
            if conv_result:
                conv_id = conv_result[0]['conversation_id']
                print(f"✓ Using existing conversation: {conv_id}")
            else:
                # Create new conversation
                print(f"🆕 Creating new conversation between {sender_id} and {receiver_id}")
                create_conv_query = """
                    INSERT INTO CONVERSATION (type, created_by)
                    VALUES ('direct', %s)
                """
                db.execute_update(create_conv_query, (sender_id,))
                conv_id = db.get_insert_id()
                print(f"✓ Created conversation: {conv_id}")
                
                # Add both participants
                add_participants_query = """
                    INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id)
                    VALUES (%s, %s), (%s, %s)
                """
                db.execute_update(add_participants_query, (conv_id, sender_id, conv_id, receiver_id))
                print(f"✓ Added participants to conversation {conv_id}")
            
            # Insert message WITH conv_id
            insert_query = """
                INSERT INTO MESSAGE (sender_id, receiver_id, content, conv_id, timestamp, status, pinned) 
                VALUES (%s, %s, %s, %s, NOW(), 'sent', FALSE)
            """
            result = db.execute_update(insert_query, (sender_id, receiver_id, content, conv_id))
            
            if not result:
                emit('message_error', {'error': 'Failed to send message'})
                print("✗ Failed to insert message")
                return
            
            msg_id = db.get_insert_id()
            print(f"✓ Message saved with ID: {msg_id}")
            
            # Update conversation last_message_at
            update_conv_query = """
                UPDATE CONVERSATION 
                SET last_message_at = NOW()
                WHERE conv_id = %s
            """
            db.execute_update(update_conv_query, (conv_id,))
            
            # Get message details
            msg_query = """
                SELECT m.msg_id, m.sender_id, m.receiver_id, m.content, 
                       m.timestamp, m.status, u.username as sender_username
                FROM MESSAGE m
                JOIN USER u ON m.sender_id = u.user_id
                WHERE m.msg_id = %s
            """
            message = db.execute_query(msg_query, (msg_id,))
            
            if message:
                msg = message[0]
                message_data = {
                    'msg_id': msg['msg_id'],
                    'sender_id': msg['sender_id'],
                    'receiver_id': msg['receiver_id'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                    'status': msg['status'],
                    'sender_username': msg['sender_username'],
                    'conv_id': conv_id
                }
                
                # Send to sender (confirmation)
                emit('message_sent', {**message_data, 'is_mine': True})
                print(f"✓ Sent confirmation to sender {sender_id}")
                
                # Send to receiver (if online)
                emit('new_message', {**message_data, 'is_mine': False}, 
                     room=f'user_{receiver_id}')
                print(f"✓ Sent message to receiver room user_{receiver_id}")
                
                # Update message status to delivered if receiver is online
                if receiver_id in online_users:
                    update_query = "UPDATE MESSAGE SET status = 'delivered' WHERE msg_id = %s"
                    db.execute_update(update_query, (msg_id,))
                    
                    emit('message_delivered', {'msg_id': msg_id, 'receiver_id': receiver_id})
                    print(f"✓ Message marked as delivered")
        
        except Exception as e:
            print(f"✗ Error in send_message: {e}")
            import traceback
            print(traceback.format_exc())
            emit('message_error', {'error': str(e)})
    
    
    @socketio.on('send_group_message')
    def handle_send_group_message(data):
        """Handle real-time group message sending"""
        sender_id = data.get('sender_id')
        group_id = data.get('group_id')
        content = data.get('content', '').strip()
        
        print(f"📨 Group message: sender={sender_id}, group={group_id}, content={content}")
        
        if not group_id or not content or not sender_id:
            emit('group_message_error', {'error': 'Missing data'})
            return
        
        try:
            # Check if user is member
            member_check = """
                SELECT 1 FROM CONVERSATION_PARTICIPANT
                WHERE conversation_id = %s AND user_id = %s
            """
            membership = db.execute_query(member_check, (group_id, sender_id))
            
            if not membership:
                emit('group_message_error', {'error': 'Not a member of this group'})
                return
            
            # Insert message (receiver_id = sender_id for group messages)
            insert_query = """
                INSERT INTO MESSAGE (sender_id, receiver_id, content, conv_id, timestamp, status, pinned)
                VALUES (%s, %s, %s, %s, NOW(), 'sent', FALSE)
            """
            result = db.execute_update(insert_query, (sender_id, sender_id, content, group_id))
            
            if not result:
                emit('group_message_error', {'error': 'Failed to send message'})
                print("✗ Failed to insert group message")
                return
            
            msg_id = db.get_insert_id()
            print(f"✓ Group message saved with ID: {msg_id}")
            
            # Update conversation last_message_at
            update_conv_query = """
                UPDATE CONVERSATION 
                SET last_message_at = NOW()
                WHERE conv_id = %s
            """
            db.execute_update(update_conv_query, (group_id,))
            
            # Get message details
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
                message_data = {
                    'msg_id': msg['msg_id'],
                    'sender_id': msg['sender_id'],
                    'sender_username': msg['sender_username'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'].isoformat() if msg['timestamp'] else None,
                    'status': msg['status'],
                    'group_id': group_id,
                    'is_group': True
                }
                
                # Broadcast to all group members (including sender for confirmation)
                emit('new_group_message', message_data, room=f'group_{group_id}')
                print(f"✓ Broadcast group message to group_{group_id}")
        
        except Exception as e:
            print(f"✗ Error in send_group_message: {e}")
            import traceback
            print(traceback.format_exc())
            emit('group_message_error', {'error': str(e)})
    
    
    @socketio.on('join_group')
    def handle_join_group(data):
        """Handle user joining a group room"""
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        
        if user_id and group_id:
            join_room(f'group_{group_id}')
            print(f"✓ User {user_id} joined group room {group_id}")
            emit('joined_group', {'group_id': group_id})
    
    
    @socketio.on('leave_group_room')
    def handle_leave_group_room(data):
        """Handle user leaving a group room"""
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        
        if user_id and group_id:
            leave_room(f'group_{group_id}')
            print(f"✓ User {user_id} left group room {group_id}")
    
    
    @socketio.on('group_typing')
    def handle_group_typing(data):
        """Handle typing indicator in group"""
        sender_id = data.get('sender_id')
        group_id = data.get('group_id')
        is_typing = data.get('is_typing', False)
        sender_username = data.get('sender_username', 'Someone')
        
        print(f"⌨️ Group typing event: sender={sender_id}, group={group_id}, typing={is_typing}")
        
        if group_id:
            emit('group_user_typing', {
                'user_id': sender_id,
                'username': sender_username,
                'is_typing': is_typing,
                'group_id': group_id
            }, room=f'group_{group_id}', include_self=False)
            print(f"✓ Sent typing indicator to group_{group_id}")
    
    
    @socketio.on('typing')
    def handle_typing(data):
        """Handle typing indicator for direct messages"""
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        is_typing = data.get('is_typing', False)
        
        print(f"⌨️ Typing event: sender={sender_id}, receiver={receiver_id}, typing={is_typing}")
        
        if receiver_id:
            emit('user_typing', {
                'user_id': sender_id,
                'is_typing': is_typing
            }, room=f'user_{receiver_id}')
            print(f"✓ Sent typing indicator to user_{receiver_id}")
    
    
    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Handle marking messages as read"""
        user_id = data.get('user_id')
        contact_id = data.get('contact_id')
        
        print(f"👁️ Mark read: user={user_id}, contact={contact_id}")
        
        if not contact_id or not user_id:
            return
        
        try:
            # Find the conversation
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
            conv_result = db.execute_query(conv_query, (user_id, contact_id))
            
            if not conv_result:
                print(f"⚠️ No conversation found between {user_id} and {contact_id}")
                return
            
            conv_id = conv_result[0]['conversation_id']
            
            # Update messages to read
            update_query = """
                UPDATE MESSAGE 
                SET status = 'read' 
                WHERE conv_id = %s
                AND receiver_id = %s 
                AND status != 'read'
            """
            db.execute_update(update_query, (conv_id, user_id))
            
            # Notify sender
            emit('messages_read', {
                'reader_id': user_id,
                'sender_id': contact_id
            }, room=f'user_{contact_id}')
            print(f"✓ Notified sender {contact_id} that messages were read")
            
        except Exception as e:
            print(f"✗ Error in mark_read: {e}")
            import traceback
            print(traceback.format_exc())
    
    
    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Get list of online users"""
        emit('online_users_list', {'users': list(online_users.keys())})
        print(f"📋 Sent online users list: {list(online_users.keys())}")
    
    
    @socketio.on('delete_message')
    def handle_delete_message(data):
        """Handle real-time message deletion"""
        sender_id = data.get('sender_id')
        msg_id = data.get('msg_id')
        receiver_id = data.get('receiver_id')
        group_id = data.get('group_id')
        
        print(f"🗑️ Delete message: msg_id={msg_id}, sender={sender_id}")
        
        if not msg_id or not sender_id:
            return
        
        delete_data = {'msg_id': msg_id, 'deleted': True}
        
        # Confirm deletion to sender
        emit('message_deleted', delete_data)
        
        # Notify others
        if group_id:
            # Group message - notify all members
            emit('message_deleted', delete_data, room=f'group_{group_id}', include_self=False)
            print(f"✓ Notified group {group_id} of deletion")
        elif receiver_id:
            # Direct message - notify receiver
            emit('message_deleted', delete_data, room=f'user_{receiver_id}')
            print(f"✓ Notified receiver {receiver_id} of deletion")
    
    
    @socketio.on('edit_message')
    def handle_edit_message(data):
        """Handle real-time message editing"""
        sender_id = data.get('sender_id')
        msg_id = data.get('msg_id')
        new_content = data.get('content')
        receiver_id = data.get('receiver_id')
        group_id = data.get('group_id')
        
        print(f"✏️ Edit message: msg_id={msg_id}, sender={sender_id}")
        
        if not msg_id or not sender_id or not new_content:
            return
        
        edit_data = {
            'msg_id': msg_id,
            'content': new_content,
            'edited': True
        }
        
        # Confirm edit to sender
        emit('message_edited', edit_data)
        
        # Notify others
        if group_id:
            # Group message - notify all members
            emit('message_edited', edit_data, room=f'group_{group_id}', include_self=False)
            print(f"✓ Notified group {group_id} of edit")
        elif receiver_id:
            # Direct message - notify receiver
            emit('message_edited', edit_data, room=f'user_{receiver_id}')
            print(f"✓ Notified receiver {receiver_id} of edit")