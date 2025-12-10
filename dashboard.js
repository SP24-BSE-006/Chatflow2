// =====================================================
// GLOBAL VARIABLES
// =====================================================
let currentUserId = parseInt(document.body.dataset.userId);
let currentUsername = document.body.dataset.username;
let currentContact = null;
let currentGroup = null;
let socket = null;
let contacts = [];
let groups = [];
let typingTimeout = null;
let selectedFile = null;

// =====================================================
// SOCKET.IO CONNECTION
// =====================================================
function connectSocket() {
    socket = io({
        query: { user_id: currentUserId },
        transports: ['websocket', 'polling']
    });
    
    socket.on('connect', () => {
        console.log('âœ… Connected to server');
        showAlert('Connected to server', 'success');
        socket.emit('get_online_users');
    });
    
    socket.on('disconnect', () => {
        console.log('âŒ Disconnected from server');
        showAlert('Disconnected from server', 'warning');
    });
    
    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        showAlert('Connection error. Retrying...', 'danger');
    });
    
    // User status events
    socket.on('user_online', (data) => {
        console.log('User online:', data.user_id);
        updateUserStatus(data.user_id, 'online');
    });
    
    socket.on('user_offline', (data) => {
        console.log('User offline:', data.user_id);
        updateUserStatus(data.user_id, 'offline');
    });
    
    socket.on('online_users_list', (data) => {
        console.log('Online users:', data.users);
        data.users.forEach(userId => updateUserStatus(userId, 'online'));
    });
    
    // Message events
    socket.on('new_message', (data) => {
        console.log('ðŸ“¨ New message received:', data);
        handleNewMessage(data);
    });
    
    socket.on('message_sent', (data) => {
        console.log('âœ… Message sent confirmation:', data);
        // Append to current chat if viewing this conversation
        if (currentContact && data.receiver_id === currentContact.user_id) {
            appendMessage(data, false);
        }
    });
    
    socket.on('message_delivered', (data) => {
        console.log('ðŸ“¬ Message delivered:', data);
        updateMessageStatus(data.msg_id, 'delivered');
    });
    
    socket.on('messages_read', (data) => {
        console.log('ðŸ‘ï¸ Messages read by:', data.reader_id);
        updateMessagesReadStatus(data.reader_id);
    });
    
    socket.on('message_deleted', (data) => {
        console.log('ðŸ—‘ï¸ Message deleted:', data);
        handleMessageDeleted(data);
    });
    
    socket.on('message_edited', (data) => {
        console.log('âœï¸ Message edited:', data);
        handleMessageEdited(data);
    });
    
    // Group message events
    socket.on('new_group_message', (data) => {
        console.log('ðŸ“¨ New group message:', data);
        handleNewGroupMessage(data);
    });
    
    // Typing indicators
    socket.on('user_typing', (data) => {
        if (currentContact && data.user_id === currentContact.user_id) {
            showTypingIndicator(data.is_typing);
        }
    });
    
    socket.on('group_user_typing', (data) => {
        if (currentGroup && data.group_id === currentGroup.group_id) {
            showGroupTypingIndicator(data.username, data.is_typing);
        }
    });
    
    // Error handling
    socket.on('message_error', (data) => {
        console.error('Message error:', data);
        showAlert(data.error || 'Failed to send message', 'danger');
    });
    
    socket.on('group_message_error', (data) => {
        console.error('Group message error:', data);
        showAlert(data.error || 'Failed to send group message', 'danger');
    });
}

// =====================================================
// INITIALIZATION
// =====================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('ðŸš€ Dashboard initialized');
    console.log('Current user:', currentUserId, currentUsername);
    
    connectSocket();
    loadContacts();
    loadGroups();
    setupEventListeners();
    setupFileUpload();
    
    // Tab switching
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', (e) => {
            if (e.target.getAttribute('href') === '#contacts-tab') {
                document.getElementById('contactsList').classList.remove('d-none');
                document.getElementById('groupsList').classList.add('d-none');
            } else {
                document.getElementById('contactsList').classList.add('d-none');
                document.getElementById('groupsList').classList.remove('d-none');
            }
        });
    });
});

// =====================================================
// EVENT LISTENERS
// =====================================================
function setupEventListeners() {
    // Search contacts
    document.getElementById('searchInput').addEventListener('input', filterContacts);
    
    // Search groups
    document.getElementById('searchGroupInput').addEventListener('input', filterGroups);
    
    // Search users for adding contacts
    document.getElementById('searchUsers').addEventListener('input', debounce(searchUsers, 300));
    
    // Send message on Enter
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Typing indicator
        chatInput.addEventListener('input', () => {
            if (currentContact) {
                socket.emit('typing', {
                    sender_id: currentUserId,
                    receiver_id: currentContact.user_id,
                    is_typing: true
                });
                
                clearTimeout(typingTimeout);
                typingTimeout = setTimeout(() => {
                    socket.emit('typing', {
                        sender_id: currentUserId,
                        receiver_id: currentContact.user_id,
                        is_typing: false
                    });
                }, 1000);
            } else if (currentGroup) {
                socket.emit('group_typing', {
                    sender_id: currentUserId,
                    group_id: currentGroup.group_id,
                    sender_username: currentUsername,
                    is_typing: true
                });
                
                clearTimeout(typingTimeout);
                typingTimeout = setTimeout(() => {
                    socket.emit('group_typing', {
                        sender_id: currentUserId,
                        group_id: currentGroup.group_id,
                        sender_username: currentUsername,
                        is_typing: false
                    });
                }, 1000);
            }
        });
    }
}

// =====================================================
// FILE UPLOAD SETUP
// =====================================================
function setupFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const btnAttach = document.getElementById('btnAttach');
    
    if (btnAttach && fileInput) {
        btnAttach.addEventListener('click', () => {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', handleFileSelect);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Check file size (50MB max)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showAlert('File too large. Maximum size is 50MB', 'danger');
        return;
    }
    
    selectedFile = file;
    showFilePreview(file);
}

function showFilePreview(file) {
    const preview = document.getElementById('fileAttachmentPreview');
    const fileName = document.getElementById('filePreviewName');
    const fileSize = document.getElementById('filePreviewSize');
    const fileIcon = document.getElementById('filePreviewIcon');
    
    if (preview && fileName && fileSize && fileIcon) {
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        // Set icon based on file type
        const iconClass = getFileIcon(file.type);
        fileIcon.className = `file-preview-icon ${iconClass}`;
        
        preview.classList.add('active');
    }
}

function removeFileAttachment() {
    selectedFile = null;
    const preview = document.getElementById('fileAttachmentPreview');
    const fileInput = document.getElementById('fileInput');
    
    if (preview) preview.classList.remove('active');
    if (fileInput) fileInput.value = '';
}

function getFileIcon(mimeType) {
    if (mimeType.startsWith('image/')) return 'fas fa-image';
    if (mimeType.startsWith('video/')) return 'fas fa-video';
    if (mimeType.startsWith('audio/')) return 'fas fa-music';
    if (mimeType.includes('pdf')) return 'fas fa-file-pdf';
    if (mimeType.includes('word')) return 'fas fa-file-word';
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fas fa-file-excel';
    if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'fas fa-file-powerpoint';
    if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('archive')) return 'fas fa-file-archive';
    return 'fas fa-file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// =====================================================
// LOAD CONTACTS
// =====================================================
async function loadContacts() {
    try {
        console.log('ðŸ“‹ Loading contacts...');
        const response = await fetch('/api/contacts/list');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('ðŸ“‹ Raw contacts data:', data);
        
        contacts = data.contacts || [];
        renderContacts();
        
        console.log('âœ… Contacts loaded:', contacts.length);
    } catch (error) {
        console.error('âŒ Error loading contacts:', error);
        showAlert('Failed to load contacts', 'danger');
        
        // Show error in UI
        const container = document.getElementById('contactsList');
        container.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #dc3545;">
                <p><i class="fas fa-exclamation-triangle"></i></p>
                <p>Failed to load contacts</p>
                <button class="btn btn-sm btn-primary mt-2" onclick="loadContacts()">Retry</button>
            </div>
        `;
    }
}

function renderContacts() {
    const container = document.getElementById('contactsList');
    
    if (contacts.length === 0) {
        container.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #999;">
                <p><i class="fas fa-user-friends"></i></p>
                <p>No contacts yet</p>
                <p><small>Click "Add Contact" to get started</small></p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = contacts.map(contact => `
        <div class="contact-item" data-user-id="${contact.user_id}" onclick="selectContact(${contact.user_id})">
            <div class="contact-info">
                <div class="contact-name">
                    <span class="status-badge ${contact.status === 'online' ? 'status-online' : 'status-offline'}"></span>
                    ${contact.username}
                </div>
                <div class="contact-status">${contact.email}</div>
            </div>
        </div>
    `).join('');
}

function filterContacts() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const items = document.querySelectorAll('#contactsList .contact-item');
    
    items.forEach(item => {
        const name = item.querySelector('.contact-name').textContent.toLowerCase();
        const email = item.querySelector('.contact-status').textContent.toLowerCase();
        
        if (name.includes(search) || email.includes(search)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// =====================================================
// LOAD GROUPS
// =====================================================
async function loadGroups() {
    try {
        console.log('ðŸ‘¥ Loading groups...');
        const response = await fetch('/api/groups/list');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('ðŸ‘¥ Raw groups data:', data);
        
        groups = data.groups || [];
        renderGroups();
        
        // Join all group rooms
        if (socket && socket.connected) {
            groups.forEach(group => {
                socket.emit('join_group', {
                    user_id: currentUserId,
                    group_id: group.group_id
                });
            });
        }
        
        console.log('âœ… Groups loaded:', groups.length);
    } catch (error) {
        console.error('âŒ Error loading groups:', error);
        showAlert('Failed to load groups', 'danger');
        
        // Show error in UI
        const container = document.getElementById('groupsList');
        container.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #dc3545;">
                <p><i class="fas fa-exclamation-triangle"></i></p>
                <p>Failed to load groups</p>
                <button class="btn btn-sm btn-primary mt-2" onclick="loadGroups()">Retry</button>
            </div>
        `;
    }
}

function renderGroups() {
    const container = document.getElementById('groupsList');
    
    if (groups.length === 0) {
        container.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #999;">
                <p><i class="fas fa-users"></i></p>
                <p>No groups yet</p>
                <p><small>Click "Create Group" to get started</small></p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = groups.map(group => `
        <div class="group-item" data-group-id="${group.group_id}" onclick="selectGroup(${group.group_id})">
            <div class="contact-info">
                <div class="contact-name">
                    <i class="fas fa-users"></i> ${group.name}
                    <span class="group-badge">${group.member_count}</span>
                </div>
                <div class="contact-status">
                    ${group.role === 'admin' ? '<i class="fas fa-crown"></i>' : ''} 
                    ${group.member_count} members
                </div>
            </div>
            ${group.unread_count > 0 ? `<span class="unread-badge">${group.unread_count}</span>` : ''}
        </div>
    `).join('');
}

function filterGroups() {
    const search = document.getElementById('searchGroupInput').value.toLowerCase();
    const items = document.querySelectorAll('#groupsList .group-item');
    
    items.forEach(item => {
        const name = item.querySelector('.contact-name').textContent.toLowerCase();
        
        if (name.includes(search)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// =====================================================
// SELECT CONTACT/GROUP
// =====================================================
async function selectContact(userId) {
    currentGroup = null;
    currentContact = contacts.find(c => c.user_id === userId);
    
    if (!currentContact) {
        console.error('Contact not found:', userId);
        return;
    }
    
    // Update UI
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-user-id="${userId}"]`).classList.add('active');
    
    // Load chat
    await loadChat(userId);
    
    // Mark messages as read
    socket.emit('mark_read', {
        user_id: currentUserId,
        contact_id: userId
    });
}

async function selectGroup(groupId) {
    currentContact = null;
    currentGroup = groups.find(g => g.group_id === groupId);
    
    if (!currentGroup) {
        console.error('Group not found:', groupId);
        return;
    }
    
    // Update UI
    document.querySelectorAll('.group-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-group-id="${groupId}"]`).classList.add('active');
    
    // Load group chat
    await loadGroupChat(groupId);
}

// =====================================================
// LOAD CHAT
// =====================================================
async function loadChat(contactId) {
    try {
        const response = await fetch(`/api/messages/history/${contactId}`);
        const data = await response.json();
        
        renderChatHeader(currentContact);
        renderMessages(data.messages || []);
        
        console.log('âœ… Chat loaded:', data.messages?.length || 0, 'messages');
    } catch (error) {
        console.error('Error loading chat:', error);
        showAlert('Failed to load chat', 'danger');
    }
}

async function loadGroupChat(groupId) {
    try {
        const response = await fetch(`/api/groups/${groupId}/messages`);
        const data = await response.json();
        
        renderGroupChatHeader(currentGroup);
        renderMessages(data.messages || [], true);
        
        console.log('âœ… Group chat loaded:', data.messages?.length || 0, 'messages');
    } catch (error) {
        console.error('Error loading group chat:', error);
        showAlert('Failed to load group chat', 'danger');
    }
}

function renderChatHeader(contact) {
    const container = document.getElementById('chatContainer');
    
    container.innerHTML = `
        <div class="chat-header">
            <div class="chat-user-info">
                <h4>
                    <span class="status-badge ${contact.status === 'online' ? 'status-online' : 'status-offline'}"></span>
                    ${contact.username}
                </h4>
                <div class="chat-user-status" id="userStatus">${contact.status}</div>
                <div class="typing-indicator d-none" id="typingIndicator">typing...</div>
            </div>
        </div>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input-container">
            <div class="file-attachment-preview" id="fileAttachmentPreview">
                <i class="file-preview-icon fas fa-file" id="filePreviewIcon"></i>
                <div class="file-preview-info">
                    <div class="file-preview-name" id="filePreviewName">filename.pdf</div>
                    <div class="file-preview-size" id="filePreviewSize">2.5 MB</div>
                </div>
                <button class="btn-remove-file" onclick="removeFileAttachment()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="input-row">
                <button class="btn-attach" id="btnAttach">
                    <i class="fas fa-paperclip"></i>
                </button>
                <input type="text" class="chat-input" id="chatInput" placeholder="Type a message...">
                <button class="btn-send" onclick="sendMessage()">
                    <i class="fas fa-paper-plane"></i> Send
                </button>
            </div>
        </div>
    `;
    
    setupEventListeners();
    setupFileUpload();
}

function renderGroupChatHeader(group) {
    const container = document.getElementById('chatContainer');
    
    container.innerHTML = `
        <div class="chat-header">
            <div class="chat-user-info">
                <h4>
                    <i class="fas fa-users"></i> ${group.name}
                </h4>
                <div class="chat-user-status">${group.member_count} members</div>
                <div class="typing-indicator d-none" id="typingIndicator">Someone is typing...</div>
            </div>
            <button class="btn btn-sm btn-outline-primary" onclick="showGroupInfo(${group.group_id})">
                <i class="fas fa-info-circle"></i> Info
            </button>
        </div>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input-container">
            <div class="file-attachment-preview" id="fileAttachmentPreview">
                <i class="file-preview-icon fas fa-file" id="filePreviewIcon"></i>
                <div class="file-preview-info">
                    <div class="file-preview-name" id="filePreviewName">filename.pdf</div>
                    <div class="file-preview-size" id="filePreviewSize">2.5 MB</div>
                </div>
                <button class="btn-remove-file" onclick="removeFileAttachment()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="input-row">
                <button class="btn-attach" id="btnAttach">
                    <i class="fas fa-paperclip"></i>
                </button>
                <input type="text" class="chat-input" id="chatInput" placeholder="Type a message...">
                <button class="btn-send" onclick="sendMessage()">
                    <i class="fas fa-paper-plane"></i> Send
                </button>
            </div>
        </div>
    `;
    
    setupEventListeners();
    setupFileUpload();
}

// =====================================================
// RENDER MESSAGES
// =====================================================
function renderMessages(messages, isGroup = false) {
    const container = document.getElementById('chatMessages');
    
    if (messages.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-comments" style="font-size: 60px; margin-bottom: 20px; opacity: 0.3;"></i>
                <p>No messages yet</p>
                <p><small>Start the conversation!</small></p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = messages.map(msg => {
        if (msg.deleted) {
            return createDeletedMessageElement(msg, isGroup);
        }
        return createMessageElement(msg, isGroup);
    }).join('');
    
    scrollToBottom();
}






// Updated function to create attachment HTML
function createAttachmentHtml(msg, isMine) {
    const isImage = msg.attachment_type === 'images';
    const originalName = msg.attachment_name || 'download';
    const downloadUrl = `/api/files/download/${msg.attachment_path}/${encodeURIComponent(originalName)}`;
    
    console.log('Creating attachment HTML:', {
        type: msg.attachment_type,
        path: msg.attachment_path,
        name: msg.attachment_name,
        isMine: isMine
    });
    
    if (isImage) {
        return `
            <div class="attachment-preview">
                <img src="/api/files/download/${msg.attachment_path}" alt="${msg.attachment_name}" 
                     onclick="openLightbox('/api/files/download/${msg.attachment_path}')"
                     onerror="console.error('Failed to load image:', '/api/files/download/${msg.attachment_path}')">
            </div>
        `;
    } else {
        const icon = getFileIconClass(msg.attachment_type);
        const attachmentId = `attachment_${msg.msg_id}`;
        
        return `
            <a href="${downloadUrl}" 
               download="${originalName}" 
               class="attachment-document" 
               id="${attachmentId}"
               onclick="handleAttachmentClick(event, '${attachmentId}')"
               style="text-decoration: none;">
                <i class="${icon} attachment-icon"></i>
                <div class="attachment-info">
                    <div class="attachment-name">${msg.attachment_name || 'Unknown file'}</div>
                    <div class="attachment-size">${formatFileSize(msg.attachment_size || 0)}</div>
                </div>
                <i class="fas fa-download attachment-download"></i>
            </a>
        `;
    }
}

// Handle attachment click to mark as downloaded
function handleAttachmentClick(event, attachmentId) {
    // Don't prevent default - allow download to proceed
    
    // Mark as downloaded after a short delay
    setTimeout(() => {
        const attachmentEl = document.getElementById(attachmentId);
        if (attachmentEl) {
            attachmentEl.classList.add('downloaded');
            console.log('Attachment marked as downloaded:', attachmentId);
        }
    }, 500);
}

// Updated message creation function
function createMessageElement(msg, isGroup) {
    const isMine = msg.sender_id === currentUserId;
    const time = formatTime(msg.timestamp);
    
    let attachmentHtml = '';
    if (msg.attachment_path) {
        attachmentHtml = createAttachmentHtml(msg, isMine);
    }
    
    return `
        <div class="message ${isMine ? 'mine' : 'theirs'}" data-msg-id="${msg.msg_id}">
            ${isMine ? `
                <div class="message-actions">
                    <button onclick="editMessage(${msg.msg_id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="deleteMessage(${msg.msg_id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            ` : ''}
            <div class="message-bubble">
                ${isGroup && !isMine ? `<div class="sender-name">${msg.sender_username}</div>` : ''}
                ${attachmentHtml}
                ${msg.content ? `<div>${msg.content}</div>` : ''}
                <div class="message-time">
                    ${time}
                    ${msg.edited ? '<span class="edited-label">(edited)</span>' : ''}
                    ${isMine ? `<div class="message-status"><i class="fas fa-check"></i></div>` : ''}
                </div>
            </div>
        </div>
    `;
}

function getFileIconClass(type) {
    const icons = {
        'documents': 'fas fa-file-alt',
        'audio': 'fas fa-music',
        'video': 'fas fa-video',
        'archives': 'fas fa-file-archive'
    };
    return icons[type] || 'fas fa-file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}





















function getFileIconClass(type) {
    const icons = {
        'documents': 'fas fa-file-alt',
        'audio': 'fas fa-music',
        'video': 'fas fa-video',
        'archives': 'fas fa-file-archive'
    };
    return icons[type] || 'fas fa-file';
}

function createDeletedMessageElement(msg, isGroup) {
    const isMine = msg.sender_id === currentUserId;
    const time = formatTime(msg.timestamp);
    
    return `
        <div class="message ${isMine ? 'mine' : 'theirs'} message-deleted" data-msg-id="${msg.msg_id}">
            <div class="message-bubble">
                ${isGroup && !isMine ? `<div class="sender-name">${msg.sender_username}</div>` : ''}
                <div><i class="fas fa-ban"></i> ${msg.content}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
}

// =====================================================
// SEND MESSAGE WITH FILE SUPPORT
// =====================================================
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const content = input.value.trim();
    
    // Must have content OR file
    if (!content && !selectedFile) {
        return;
    }
    
    let attachmentData = null;
    
    // Upload file first if selected
    if (selectedFile) {
        console.log('ðŸ“Ž Uploading file:', selectedFile.name);
        attachmentData = await uploadFile(selectedFile);
        if (!attachmentData) {
            showAlert('Failed to upload file', 'danger');
            return;
        }
        console.log('âœ… File uploaded:', attachmentData);
    }
    
    if (currentContact) {
        console.log('ðŸ“¨ Sending direct message to:', currentContact.user_id);
        // Send direct message
        socket.emit('send_message', {
            sender_id: currentUserId,
            receiver_id: currentContact.user_id,
            content: content,
            attachment_path: attachmentData?.filename,
            attachment_name: attachmentData?.original_name,
            attachment_type: attachmentData?.type,
            attachment_size: attachmentData?.size
        });
    } else if (currentGroup) {
        console.log('ðŸ“¨ Sending group message to:', currentGroup.group_id);
        // Send group message
        socket.emit('send_group_message', {
            sender_id: currentUserId,
            group_id: currentGroup.group_id,
            content: content,
            attachment_path: attachmentData?.filename,
            attachment_name: attachmentData?.original_name,
            attachment_type: attachmentData?.type,
            attachment_size: attachmentData?.size
        });
    }
    
    input.value = '';
    removeFileAttachment();
}

async function uploadFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            return data.file;
        } else {
            console.error('Upload failed:', data.error);
            return null;
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        return null;
    }
}

// =====================================================
// MESSAGE HANDLERS
// =====================================================
function handleNewMessage(data) {
    if (currentContact && data.sender_id === currentContact.user_id) {
        appendMessage(data, false);
        
        // Mark as read
        socket.emit('mark_read', {
            user_id: currentUserId,
            contact_id: currentContact.user_id
        });
    } else {
        // Update unread count
        showAlert(`New message from ${data.sender_username}`, 'info');
    }
}

function handleNewGroupMessage(data) {
    console.log('ðŸ“¨ Handling group message:', data);
    if (currentGroup && data.group_id === currentGroup.group_id) {
        appendMessage(data, true);
    } else {
        // Update unread count
        showAlert(`New message in group`, 'info');
    }
}

function appendMessage(msg, isGroup) {
    const container = document.getElementById('chatMessages');
    
    // Remove empty state if present
    if (container.querySelector('.fas.fa-comments')) {
        container.innerHTML = '';
    }
    
    const messageHtml = createMessageElement(msg, isGroup);
    container.insertAdjacentHTML('beforeend', messageHtml);
    scrollToBottom();
}

function handleMessageDeleted(data) {
    const messageEl = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (messageEl) {
        messageEl.classList.add('message-deleted');
        const bubble = messageEl.querySelector('.message-bubble');
        bubble.innerHTML = `
            <div><i class="fas fa-ban"></i> This message was deleted</div>
            <div class="message-time">${bubble.querySelector('.message-time')?.innerHTML || ''}</div>
        `;
    }
}

function handleMessageEdited(data) {
    const messageEl = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (messageEl) {
        const contentEl = messageEl.querySelector('.message-bubble > div:first-child');
        if (contentEl) {
            contentEl.textContent = data.content;
            const timeEl = messageEl.querySelector('.message-time');
            if (timeEl && !timeEl.querySelector('.edited-label')) {
                timeEl.insertAdjacentHTML('beforeend', '<span class="edited-label">(edited)</span>');
            }
        }
    }
}

// =====================================================
// DELETE/EDIT MESSAGE
// =====================================================
async function deleteMessage(msgId) {
    if (!confirm('Delete this message?')) return;
    
    try {
        const response = await fetch(`/api/messages/delete/${msgId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            socket.emit('delete_message', {
                sender_id: currentUserId,
                msg_id: msgId,
                receiver_id: currentContact?.user_id,
                group_id: currentGroup?.group_id
            });
        } else {
            showAlert(data.error || 'Failed to delete message', 'danger');
        }
    } catch (error) {
        console.error('Error deleting message:', error);
        showAlert('Failed to delete message', 'danger');
    }
}

async function editMessage(msgId) {
    const messageEl = document.querySelector(`[data-msg-id="${msgId}"]`);
    const contentEl = messageEl.querySelector('.message-bubble > div:first-child');
    const currentContent = contentEl.textContent;
    
    const newContent = prompt('Edit message:', currentContent);
    
    if (!newContent || newContent === currentContent) return;
    
    try {
        const response = await fetch(`/api/messages/edit/${msgId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });
        
        const data = await response.json();
        
        if (data.success) {
            socket.emit('edit_message', {
                sender_id: currentUserId,
                msg_id: msgId,
                content: newContent,
                receiver_id: currentContact?.user_id,
                group_id: currentGroup?.group_id
            });
        } else {
            showAlert(data.error || 'Failed to edit message', 'danger');
        }
    } catch (error) {
        console.error('Error editing message:', error);
        showAlert('Failed to edit message', 'danger');
    }
}

// =====================================================
// TYPING INDICATORS
// =====================================================
function showTypingIndicator(isTyping) {
    const indicator = document.getElementById('typingIndicator');
    const status = document.getElementById('userStatus');
    
    if (indicator && status) {
        if (isTyping) {
            status.classList.add('d-none');
            indicator.classList.remove('d-none');
        } else {
            status.classList.remove('d-none');
            indicator.classList.add('d-none');
        }
    }
}

function showGroupTypingIndicator(username, isTyping) {
    const indicator = document.getElementById('typingIndicator');
    
    if (indicator) {
        if (isTyping) {
            indicator.textContent = `${username} is typing...`;
            indicator.classList.remove('d-none');
        } else {
            indicator.classList.add('d-none');
        }
    }
}

// =====================================================
// UPDATE USER STATUS
// =====================================================
function updateUserStatus(userId, status) {
    // Update in contacts list
    const contactItem = document.querySelector(`[data-user-id="${userId}"]`);
    if (contactItem) {
        const badge = contactItem.querySelector('.status-badge');
        if (badge) {
            badge.className = `status-badge ${status === 'online' ? 'status-online' : 'status-offline'}`;
        }
    }
    
    // Update in chat header if currently chatting
    if (currentContact && currentContact.user_id === userId) {
        const headerBadge = document.querySelector('.chat-header .status-badge');
        const statusText = document.getElementById('userStatus');
        
        if (headerBadge) {
            headerBadge.className = `status-badge ${status === 'online' ? 'status-online' : 'status-offline'}`;
        }
        if (statusText) {
            statusText.textContent = status;
        }
    }
}

function updateMessageStatus(msgId, status) {
    const messageEl = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (messageEl) {
        const statusEl = messageEl.querySelector('.message-status i');
        if (statusEl && status === 'delivered') {
            statusEl.className = 'fas fa-check-double';
        }
    }
}

function updateMessagesReadStatus(readerId) {
    if (currentContact && currentContact.user_id === readerId) {
        document.querySelectorAll('.message.mine .message-status i').forEach(icon => {
            icon.className = 'fas fa-check-double';
            icon.style.color = '#4CAF50';
        });
    }
}

// =====================================================
// SEARCH USERS
// =====================================================
async function searchUsers() {
    const query = document.getElementById('searchUsers').value.trim();
    const resultsDiv = document.getElementById('searchResults');
    
    if (query.length < 2) {
        resultsDiv.classList.add('d-none');
        return;
    }
    
    try {
        const response = await fetch(`/api/contacts/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.results.length === 0) {
            resultsDiv.innerHTML = '<div style="padding: 15px; text-align: center; color: #999;">No users found</div>';
        } else {
            resultsDiv.innerHTML = data.results.map(user => `
                <div class="search-result-item">
                    <div>
                        <strong>${user.username}</strong>
                        <br><small>${user.email}</small>
                    </div>
                    ${user.is_contact ? 
                        '<span class="badge bg-success">Contact</span>' : 
                        `<button class="btn btn-sm btn-primary" onclick="addContact(${user.user_id})">Add</button>`
                    }
                </div>
            `).join('');
        }
        
        resultsDiv.classList.remove('d-none');
    } catch (error) {
        console.error('Error searching users:', error);
        showAlert('Failed to search users', 'danger');
    }
}

async function addContact(userId) {
    try {
        const response = await fetch('/api/contacts/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contact_user_id: userId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Contact added successfully', 'success');
            await loadContacts();
            searchUsers(); // Refresh search results
        } else {
            showAlert(data.error || 'Failed to add contact', 'danger');
        }
    } catch (error) {
        console.error('Error adding contact:', error);
        showAlert('Failed to add contact', 'danger');
    }
}

// =====================================================
// GROUP FUNCTIONS
// =====================================================
async function createGroup() {
    const nameInput = document.getElementById('groupName');
    const name = nameInput.value.trim();
    
    if (!name) {
        showAlert('Please enter a group name', 'warning');
        return;
    }
    
    const selectedMembers = Array.from(document.querySelectorAll('.member-item.member-selected'))
        .map(item => parseInt(item.dataset.userId));
    
    if (selectedMembers.length === 0) {
        showAlert('Please select at least one member', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/groups/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                members: selectedMembers,
                privacy: 'private'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Group created successfully', 'success');
            await loadGroups();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
            modal.hide();
            
            // Reset form
            nameInput.value = '';
        } else {
            showAlert(data.error || 'Failed to create group', 'danger');
        }
    } catch (error) {
        console.error('Error creating group:', error);
        showAlert('Failed to create group', 'danger');
    }
}

// Load contacts for group creation
document.getElementById('createGroupModal')?.addEventListener('show.bs.modal', async () => {
    const membersList = document.getElementById('membersList');
    
    membersList.innerHTML = contacts.map(contact => `
        <div class="member-item" data-user-id="${contact.user_id}" 
             onclick="toggleMember(${contact.user_id})">
            <div>
                <strong>${contact.username}</strong>
                <br><small>${contact.email}</small>
            </div>
            <input type="checkbox" class="form-check-input">
        </div>
    `).join('');
});

function toggleMember(userId) {
    const item = document.querySelector(`.member-item[data-user-id="${userId}"]`);
    const checkbox = item.querySelector('input[type="checkbox"]');
    
    item.classList.toggle('member-selected');
    checkbox.checked = !checkbox.checked;
}

async function showGroupInfo(groupId) {
    try {
        const response = await fetch(`/api/groups/${groupId}`);
        const data = await response.json();
        
        if (data.success) {
            const group = data.group;
            const content = document.getElementById('groupInfoContent');
            
            content.innerHTML = `
                <div class="mb-3">
                    <h5>${group.name}</h5>
                    <p class="text-muted">Created by ${group.creator_username}</p>
                </div>
                
                <div class="mb-3">
                    <h6>Members (${group.members.length})</h6>
                    <div class="list-group">
                        ${group.members.map(member => `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <strong>${member.username}</strong>
                                        ${member.role === 'admin' ? '<i class="fas fa-crown text-warning ms-2"></i>' : ''}
                                        <br><small class="text-muted">${member.email}</small>
                                    </div>
                                    ${group.user_role === 'admin' && member.user_id !== group.created_by ? 
                                        `<button class="btn btn-sm btn-danger" onclick="removeMember(${groupId}, ${member.user_id})">
                                            <i class="fas fa-times"></i>
                                        </button>` : ''
                                    }
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                ${group.user_role === 'admin' && group.created_by === currentUserId ? 
                    `<button class="btn btn-danger w-100" onclick="deleteGroup(${groupId})">
                        <i class="fas fa-trash"></i> Delete Group
                    </button>` : 
                    `<button class="btn btn-warning w-100" onclick="leaveGroup(${groupId})">
                        <i class="fas fa-sign-out-alt"></i> Leave Group
                    </button>`
                }
            `;
            
            const modal = new bootstrap.Modal(document.getElementById('groupInfoModal'));
            modal.show();
        }
    } catch (error) {
        console.error('Error loading group info:', error);
        showAlert('Failed to load group info', 'danger');
    }
}

async function removeMember(groupId, memberId) {
    if (!confirm('Remove this member from the group?')) return;
    
    try {
        const response = await fetch(`/api/groups/${groupId}/remove-member/${memberId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Member removed', 'success');
            showGroupInfo(groupId); // Refresh
        } else {
            showAlert(data.error || 'Failed to remove member', 'danger');
        }
    } catch (error) {
        console.error('Error removing member:', error);
        showAlert('Failed to remove member', 'danger');
    }
}

async function leaveGroup(groupId) {
    if (!confirm('Leave this group?')) return;
    
    try {
        const response = await fetch(`/api/groups/${groupId}/leave`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Left group successfully', 'success');
            await loadGroups();
            
            // Close modal and clear chat
            const modal = bootstrap.Modal.getInstance(document.getElementById('groupInfoModal'));
            modal.hide();
            
            document.getElementById('chatContainer').innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comments"></i>
                    <h3>Select a contact or group to start chatting</h3>
                </div>
            `;
        } else {
            showAlert(data.error || 'Failed to leave group', 'danger');
        }
    } catch (error) {
        console.error('Error leaving group:', error);
        showAlert('Failed to leave group', 'danger');
    }
}

async function deleteGroup(groupId) {
    if (!confirm('Delete this group? This cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/groups/${groupId}/delete`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Group deleted successfully', 'success');
            await loadGroups();
            
            // Close modal and clear chat
            const modal = bootstrap.Modal.getInstance(document.getElementById('groupInfoModal'));
            modal.hide();
            
            document.getElementById('chatContainer').innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comments"></i>
                    <h3>Select a contact or group to start chatting</h3>
                </div>
            `;
        } else {
            showAlert(data.error || 'Failed to delete group', 'danger');
        }
    } catch (error) {
        console.error('Error deleting group:', error);
        showAlert('Failed to delete group', 'danger');
    }
}

// =====================================================
// IMAGE LIGHTBOX
// =====================================================
function openLightbox(imageUrl) {
    const lightbox = document.getElementById('imageLightbox');
    const image = document.getElementById('lightboxImage');
    
    image.src = imageUrl;
    lightbox.classList.add('active');
}

function closeLightbox() {
    const lightbox = document.getElementById('imageLightbox');
    lightbox.classList.remove('active');
}

// =====================================================
// UTILITY FUNCTIONS
// =====================================================
function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 86400000) { // Less than 24 hours
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (diff < 604800000) { // Less than 7 days
        return date.toLocaleDateString('en-US', { weekday: 'short', hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', alertHtml);
    
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) {
            alert.remove();
        }
    }, 5000);
}