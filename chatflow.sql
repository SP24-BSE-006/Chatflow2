CREATE DATABASE IF NOT EXISTS messaging_app_db;

USE messaging_app_db;


CREATE TABLE IF NOT EXISTS USER (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('online', 'offline') DEFAULT 'offline',
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    role ENUM('user', 'admin') DEFAULT 'user',
    profile_photo_privacy ENUM('everyone', 'friends', 'no_one') DEFAULT 'everyone',
    group_add_privacy ENUM('everyone', 'friends', 'no_one') DEFAULT 'everyone',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS CONVERSATION (
    conv_id INT AUTO_INCREMENT PRIMARY KEY,
    user1_id INT NOT NULL,
    user2_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user1_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_conversation (user1_id, user2_id),
    INDEX idx_user1 (user1_id),
    INDEX idx_user2 (user2_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS MESSAGE (
    msg_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    attachment_path VARCHAR(255),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('sent', 'delivered', 'read') DEFAULT 'sent',
    pinned BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (sender_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_sender (sender_id),
    INDEX idx_receiver (receiver_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS USERBLOCK (
    blocker_id INT NOT NULL,
    blocked_id INT NOT NULL,
    blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (blocker_id, blocked_id),
    FOREIGN KEY (blocker_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_blocker (blocker_id),
    INDEX idx_blocked (blocked_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS USERCONTACT (
    user_id INT NOT NULL,
    contact_user_id INT NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, contact_user_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (contact_user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_contact (contact_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS STARREDMESSAGES (
    user_id INT NOT NULL,
    msg_id INT NOT NULL,
    starred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, msg_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (msg_id) REFERENCES MESSAGE(msg_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_msg (msg_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS ARCHIVEDMESSAGES (
    user_id INT NOT NULL,
    msg_id INT NOT NULL,
    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, msg_id),
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (msg_id) REFERENCES MESSAGE(msg_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_msg (msg_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS USERACTIVITYLOG (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action VARCHAR(255) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS ADMINACTION (
    admin_action_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action_description TEXT NOT NULL,
    target_user_id INT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (target_user_id) REFERENCES USER(user_id) ON DELETE SET NULL,
    INDEX idx_admin (admin_id),
    INDEX idx_target (target_user_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS USER_GROUP(
    group_id INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    privacy_settings ENUM('public', 'private') DEFAULT 'private',
    FOREIGN KEY (created_by) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_created_by (created_by),
    INDEX idx_group_name (group_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS GROUPMEMBER (
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('admin', 'member') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES USER_GROUP(group_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_group (group_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS GROUPMESSAGE (
    msg_id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    sender_id INT NOT NULL,
    content TEXT NOT NULL,
    attachment_path VARCHAR(255),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('sent', 'delivered', 'read') DEFAULT 'sent',
    FOREIGN KEY (group_id) REFERENCES USER_GROUP(group_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_group (group_id),
    INDEX idx_sender (sender_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE MESSAGE 
ADD COLUMN edited BOOLEAN DEFAULT FALSE,
ADD COLUMN edited_at DATETIME NULL;


ALTER TABLE MESSAGE 
ADD COLUMN deleted BOOLEAN DEFAULT FALSE,
ADD COLUMN deleted_at DATETIME NULL;






DROP TABLE IF EXISTS CONVERSATION;

CREATE TABLE IF NOT EXISTS CONVERSATION (
    conv_id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('direct', 'group') NOT NULL DEFAULT 'direct',
    name VARCHAR(100) NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP NULL,
    privacy_settings ENUM('public', 'private') DEFAULT 'private',
    FOREIGN KEY (created_by) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_type (type),
    INDEX idx_created_by (created_by),
    INDEX idx_last_message (last_message_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS CONVERSATION_PARTICIPANT (
    conversation_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('admin', 'member') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_msg_id INT NULL,
    muted BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (conversation_id, user_id),
    FOREIGN KEY (conversation_id) REFERENCES CONVERSATION(conv_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    INDEX idx_conversation (conversation_id),
    INDEX idx_user (user_id),
    INDEX idx_user_archived (user_id, archived)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


ALTER TABLE MESSAGE 
ADD COLUMN conv_id INT NULL AFTER receiver_id;



-- Create one conversation per unique user pair
INSERT INTO CONVERSATION (type, created_by, created_at, last_message_at)
SELECT 
    'direct' as type,
    LEAST(sender_id, receiver_id) as created_by,
    MIN(timestamp) as created_at,
    MAX(timestamp) as last_message_at
FROM MESSAGE
GROUP BY LEAST(sender_id, receiver_id), GREATEST(sender_id, receiver_id);


SELECT COUNT(*) as conversations_created FROM CONVERSATION;


INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, joined_at)

SELECT 
    c.conv_id,
    c.created_by as user_id,
    c.created_at
FROM CONVERSATION c
WHERE c.type = 'direct';

-- Add the "higher ID" user as participant
-- We need to find them from the messages
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, joined_at)
SELECT DISTINCT
    c.conv_id,
    GREATEST(m.sender_id, m.receiver_id) as user_id,
    c.created_at
FROM CONVERSATION c
JOIN MESSAGE m ON (
    LEAST(m.sender_id, m.receiver_id) = c.created_by
    AND c.type = 'direct'
)
WHERE GREATEST(m.sender_id, m.receiver_id) != c.created_by;

-- Verify participants (should be 2x number of conversations)
SELECT COUNT(*) as total_participants FROM CONVERSATION_PARTICIPANT;
SELECT COUNT(*) * 2 as expected_participants FROM CONVERSATION WHERE type = 'direct';

-- Clear the CONVERSATION_PARTICIPANT table
DELETE FROM CONVERSATION_PARTICIPANT;

-- Verify it's empty
SELECT COUNT(*) FROM CONVERSATION_PARTICIPANT;
-- Should show 0

-- Now run the INSERT again (will work this time)
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, joined_at)
SELECT DISTINCT
    c.conv_id,
    m.sender_id as user_id,
    c.created_at
FROM CONVERSATION c
JOIN MESSAGE m ON LEAST(m.sender_id, m.receiver_id) = c.created_by
WHERE c.type = 'direct'

UNION

SELECT DISTINCT
    c.conv_id,
    m.receiver_id as user_id,
    c.created_at
FROM CONVERSATION c
JOIN MESSAGE m ON LEAST(m.sender_id, m.receiver_id) = c.created_by
WHERE c.type = 'direct';

-- Verify it worked
SELECT COUNT(*) as total_participants FROM CONVERSATION_PARTICIPANT;
SELECT 
    conversation_id,
    COUNT(*) as participant_count
FROM CONVERSATION_PARTICIPANT
GROUP BY conversation_id;
-- Each conversation should have 2 participants


-- See which users are in conversation 1
SELECT 
    cp.conversation_id,
    cp.user_id,
    u.username
FROM CONVERSATION_PARTICIPANT cp
JOIN USER u ON u.user_id = cp.user_id
WHERE cp.conversation_id = 1;









SET SQL_SAFE_UPDATES = 0;

-- Link all messages to their conversations
UPDATE MESSAGE m
SET m.conv_id = (
    SELECT c.conv_id
    FROM CONVERSATION c
    WHERE c.type = 'direct'
      AND c.created_by = LEAST(m.sender_id, m.receiver_id)
    LIMIT 1
);

-- Re-enable safe updates
SET SQL_SAFE_UPDATES = 1;

-- Verify ALL messages are linked
SELECT 
    COUNT(*) as total_messages,
    SUM(CASE WHEN conv_id IS NOT NULL THEN 1 ELSE 0 END) as linked_messages,
    SUM(CASE WHEN conv_id IS NULL THEN 1 ELSE 0 END) as orphan_messages
FROM MESSAGE;

-- orphan_messages MUST be 0!

-- Make conv_id required (no longer nullable)
ALTER TABLE MESSAGE 
MODIFY COLUMN conv_id INT NOT NULL;

-- Add foreign key constraint
ALTER TABLE MESSAGE
ADD CONSTRAINT fk_message_conversation 
FOREIGN KEY (conv_id) REFERENCES CONVERSATION(conv_id) ON DELETE CASCADE;

-- Add index for fast queries
CREATE INDEX idx_message_conv ON MESSAGE(conv_id, timestamp);

-- Verify constraint was added
SHOW CREATE TABLE MESSAGE;


-- Drop the old empty group tables (we don't need them anymore)
DROP TABLE IF EXISTS GROUPMESSAGE;
DROP TABLE IF EXISTS GROUPMEMBER;
DROP TABLE IF EXISTS USER_GROUP;


SELECT COUNT(*) as total_users FROM USER;
SELECT COUNT(*) as total_conversations FROM CONVERSATION;
SELECT COUNT(*) as total_participants FROM CONVERSATION_PARTICIPANT;
SELECT COUNT(*) as total_messages FROM MESSAGE;

SELECT 
    c.conv_id,
    c.type,
    GROUP_CONCAT(DISTINCT u.username ORDER BY u.username SEPARATOR ', ') as participants,
    (SELECT COUNT(*) FROM MESSAGE m WHERE m.conv_id = c.conv_id) as message_count,
    c.last_message_at
FROM CONVERSATION c
JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
JOIN USER u ON u.user_id = cp.user_id
GROUP BY c.conv_id
LIMIT 5;

SELECT * FROM CONVERSATION;
SELECT * FROM USERCONTACT;
SELECT * FROM MESSAGE;
SELECT * FROM USER;
SELECT * FROM CONVERSATION_PARTICIPANT;































-- ============================================
-- MIGRATION: Create conversations for existing contacts
-- ============================================

-- Step 1: Create conversations for all unique contact pairs
INSERT INTO CONVERSATION (type, created_by, created_at, privacy_settings)
SELECT DISTINCT
    'direct' as type,
    LEAST(uc.user_id, uc.contact_user_id) as created_by,
    MIN(uc.added_at) as created_at,
    'private' as privacy_settings
FROM USERCONTACT uc
WHERE NOT EXISTS (
    -- Only create if conversation doesn't already exist
    SELECT 1 
    FROM CONVERSATION c
    JOIN CONVERSATION_PARTICIPANT cp1 ON cp1.conversation_id = c.conv_id
    JOIN CONVERSATION_PARTICIPANT cp2 ON cp2.conversation_id = c.conv_id
    WHERE c.type = 'direct'
    AND ((cp1.user_id = uc.user_id AND cp2.user_id = uc.contact_user_id)
         OR (cp1.user_id = uc.contact_user_id AND cp2.user_id = uc.user_id))
)
GROUP BY LEAST(uc.user_id, uc.contact_user_id), GREATEST(uc.user_id, uc.contact_user_id);

-- Verify: Check how many conversations were created
SELECT COUNT(*) as new_conversations_created FROM CONVERSATION WHERE type = 'direct';


-- Step 2: Add participants (User 1) for all contact pairs
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role, joined_at)
SELECT DISTINCT
    c.conv_id,
    uc.user_id,
    'member' as role,
    uc.added_at as joined_at
FROM USERCONTACT uc
JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id)
WHERE c.type = 'direct'
AND NOT EXISTS (
    SELECT 1 FROM CONVERSATION_PARTICIPANT cp
    WHERE cp.conversation_id = c.conv_id
    AND cp.user_id = uc.user_id
);

-- Step 3: Add participants (User 2) for all contact pairs
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role, joined_at)
SELECT DISTINCT
    c.conv_id,
    uc.contact_user_id,
    'member' as role,
    uc.added_at as joined_at
FROM USERCONTACT uc
JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id)
WHERE c.type = 'direct'
AND NOT EXISTS (
    SELECT 1 FROM CONVERSATION_PARTICIPANT cp
    WHERE cp.conversation_id = c.conv_id
    AND cp.user_id = uc.contact_user_id
);

-- Verify: Each direct conversation should have exactly 2 participants
SELECT 
    c.conv_id,
    c.name,
    COUNT(cp.user_id) as participant_count,
    GROUP_CONCAT(u.username) as participants
FROM CONVERSATION c
JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
JOIN USER u ON u.user_id = cp.user_id
WHERE c.type = 'direct'
GROUP BY c.conv_id
HAVING participant_count != 2;
-- This should return 0 rows if everything is correct


-- Step 4: Link existing orphan messages to conversations (if any)
-- Find messages that don't have conv_id set
UPDATE MESSAGE m
SET m.conv_id = (
    SELECT c.conv_id
    FROM CONVERSATION c
    JOIN CONVERSATION_PARTICIPANT cp1 ON cp1.conversation_id = c.conv_id
    JOIN CONVERSATION_PARTICIPANT cp2 ON cp2.conversation_id = c.conv_id
    WHERE c.type = 'direct'
    AND ((cp1.user_id = m.sender_id AND cp2.user_id = m.receiver_id)
         OR (cp1.user_id = m.receiver_id AND cp2.user_id = m.sender_id))
    AND cp1.user_id != cp2.user_id
    LIMIT 1
)
WHERE m.conv_id IS NULL OR m.conv_id = 0;

-- Verify: Check if any messages are still orphaned
SELECT COUNT(*) as orphan_messages 
FROM MESSAGE 
WHERE conv_id IS NULL OR conv_id = 0;
-- This should be 0


-- Step 5: Update last_message_at for all conversations based on actual messages
UPDATE CONVERSATION c
SET last_message_at = (
    SELECT MAX(m.timestamp)
    FROM MESSAGE m
    WHERE m.conv_id = c.conv_id
)
WHERE c.type = 'direct';


-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- 1. Show all direct conversations with participants
SELECT 
    c.conv_id,
    GROUP_CONCAT(u.username ORDER BY u.username SEPARATOR ' & ') as conversation_between,
    COUNT(cp.user_id) as participants,
    c.created_at,
    c.last_message_at,
    (SELECT COUNT(*) FROM MESSAGE WHERE conv_id = c.conv_id) as message_count
FROM CONVERSATION c
JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
JOIN USER u ON u.user_id = cp.user_id
WHERE c.type = 'direct'
GROUP BY c.conv_id
ORDER BY c.last_message_at DESC;

-- 2. Show all contacts and their conversation status
SELECT 
    u1.username as user,
    u2.username as contact,
    uc.added_at,
    c.conv_id,
    CASE WHEN c.conv_id IS NULL THEN '❌ Missing' ELSE '✅ Exists' END as conversation_status
FROM USERCONTACT uc
JOIN USER u1 ON u1.user_id = uc.user_id
JOIN USER u2 ON u2.user_id = uc.contact_user_id
LEFT JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id)
LEFT JOIN CONVERSATION_PARTICIPANT cp1 ON cp1.conversation_id = c.conv_id AND cp1.user_id = uc.user_id
LEFT JOIN CONVERSATION_PARTICIPANT cp2 ON cp2.conversation_id = c.conv_id AND cp2.user_id = uc.contact_user_id
WHERE c.type = 'direct' OR c.type IS NULL
ORDER BY u1.username, u2.username;

-- 3. Final summary
SELECT 
    'Total Users' as metric, COUNT(*) as count FROM USER
UNION ALL
SELECT 'Total Contacts', COUNT(*) FROM USERCONTACT
UNION ALL
SELECT 'Total Direct Conversations', COUNT(*) FROM CONVERSATION WHERE type = 'direct'
UNION ALL
SELECT 'Total Group Conversations', COUNT(*) FROM CONVERSATION WHERE type = 'group'
UNION ALL
SELECT 'Total Participants', COUNT(*) FROM CONVERSATION_PARTICIPANT
UNION ALL
SELECT 'Total Messages', COUNT(*) FROM MESSAGE
UNION ALL
SELECT 'Messages with Conversations', COUNT(*) FROM MESSAGE WHERE conv_id IS NOT NULL;











-- ============================================
-- COMPLETE CLEANUP: Remove all conversation data

ALTER TABLE MESSAGE MODIFY COLUMN conv_id INT NULL;
-- ============================================
SET SQL_SAFE_UPDATES = 0;
-- Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;

-- Step 1: Delete ALL conversation-related data
DELETE FROM CONVERSATION_PARTICIPANT;
DELETE FROM CONVERSATION WHERE type = 'direct';

-- Also clear conv_id from messages (we'll re-link them later)
UPDATE MESSAGE SET conv_id = NULL WHERE conv_id IS NOT NULL;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Verify cleanup
SELECT 'Direct Conversations' as table_name, COUNT(*) as remaining_rows 
FROM CONVERSATION WHERE type = 'direct'
UNION ALL
SELECT 'Conversation Participants', COUNT(*) 
FROM CONVERSATION_PARTICIPANT
UNION ALL
SELECT 'Messages with conv_id', COUNT(*) 
FROM MESSAGE WHERE conv_id IS NOT NULL;
-- All should show 0


-- ============================================
-- FRESH MIGRATION: Create conversations ONLY for contacts
-- ============================================

-- Step 1: Show what contacts we have
SELECT 
    'Existing Contacts' as info,
    u1.username as user,
    u2.username as contact
FROM USERCONTACT uc
JOIN USER u1 ON u1.user_id = uc.user_id
JOIN USER u2 ON u2.user_id = uc.contact_user_id
ORDER BY u1.username;
-- Verify this matches your expected contacts


-- Step 2: Create ONE conversation for each UNIQUE contact pair
-- Key: Use LEAST/GREATEST to treat (user1, user2) and (user2, user1) as same pair
INSERT INTO CONVERSATION (type, created_by, created_at, privacy_settings)
SELECT 
    'direct' as type,
    LEAST(user1_id, user2_id) as created_by,
    MIN(added_at) as created_at,
    'private' as privacy_settings
FROM (
    -- Get all unique user pairs from USERCONTACT
    SELECT DISTINCT
        uc1.user_id as user1_id,
        uc1.contact_user_id as user2_id,
        uc1.added_at
    FROM USERCONTACT uc1
    
    UNION
    
    -- Also include reverse relationships if they exist
    SELECT DISTINCT
        uc2.contact_user_id as user1_id,
        uc2.user_id as user2_id,
        uc2.added_at
    FROM USERCONTACT uc2
) as all_pairs
GROUP BY LEAST(user1_id, user2_id), GREATEST(user1_id, user2_id);

-- Check how many conversations were created
SELECT COUNT(*) as conversations_created 
FROM CONVERSATION 
WHERE type = 'direct';


-- Step 3: Add participants (both users in each conversation)
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role, joined_at)
SELECT 
    c.conv_id,
    all_participants.user_id,
    'member' as role,
    c.created_at as joined_at
FROM CONVERSATION c
CROSS JOIN (
    -- For each conversation, get both user IDs
    SELECT DISTINCT
        LEAST(uc.user_id, uc.contact_user_id) as lower_id,
        GREATEST(uc.user_id, uc.contact_user_id) as higher_id
    FROM USERCONTACT uc
) as pairs
CROSS JOIN (
    SELECT 1 as seq, pairs.lower_id as user_id
    UNION ALL
    SELECT 2 as seq, pairs.higher_id as user_id
) as all_participants
WHERE c.type = 'direct'
AND c.created_by = pairs.lower_id;

-- Simpler approach - Add participants one by one
-- Clear the table first
DELETE FROM CONVERSATION_PARTICIPANT;

-- Add user (the one who has the contact)
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role, joined_at)
SELECT DISTINCT
    c.conv_id,
    uc.user_id,
    'member' as role,
    uc.added_at as joined_at
FROM USERCONTACT uc
JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id)
WHERE c.type = 'direct';

-- Add contact_user
INSERT INTO CONVERSATION_PARTICIPANT (conversation_id, user_id, role, joined_at)
SELECT DISTINCT
    c.conv_id,
    uc.contact_user_id,
    'member' as role,
    uc.added_at as joined_at
FROM USERCONTACT uc
JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id)
WHERE c.type = 'direct'
AND NOT EXISTS (
    SELECT 1 FROM CONVERSATION_PARTICIPANT cp
    WHERE cp.conversation_id = c.conv_id
    AND cp.user_id = uc.contact_user_id
);


-- Step 4: Verify each conversation has EXACTLY 2 participants
SELECT 
    c.conv_id,
    COUNT(cp.user_id) as participant_count,
    GROUP_CONCAT(u.username ORDER BY u.username SEPARATOR ' & ') as participants
FROM CONVERSATION c
JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
JOIN USER u ON u.user_id = cp.user_id
WHERE c.type = 'direct'
GROUP BY c.conv_id
HAVING participant_count != 2;
-- This should return ZERO rows (all conversations should have 2 participants)


-- Step 5: Link messages to conversations
UPDATE MESSAGE m
JOIN CONVERSATION_PARTICIPANT cp1 ON cp1.user_id = m.sender_id
JOIN CONVERSATION_PARTICIPANT cp2 ON cp2.user_id = m.receiver_id
JOIN CONVERSATION c ON c.conv_id = cp1.conversation_id
SET m.conv_id = c.conv_id
WHERE c.type = 'direct'
AND cp1.conversation_id = cp2.conversation_id
AND m.conv_id IS NULL;


-- Step 6: Update last_message_at
UPDATE CONVERSATION c
SET last_message_at = (
    SELECT MAX(m.timestamp)
    FROM MESSAGE m
    WHERE m.conv_id = c.conv_id
)
WHERE c.type = 'direct'
AND EXISTS (SELECT 1 FROM MESSAGE WHERE conv_id = c.conv_id);


-- ============================================
-- FINAL VERIFICATION
-- ============================================

-- 1. Show all conversations with their participants
SELECT 
    c.conv_id,
    GROUP_CONCAT(u.username ORDER BY u.username SEPARATOR ' & ') as conversation,
    COUNT(cp.user_id) as participants,
    (SELECT COUNT(*) FROM MESSAGE WHERE conv_id = c.conv_id) as messages,
    c.created_at
FROM CONVERSATION c
JOIN CONVERSATION_PARTICIPANT cp ON cp.conversation_id = c.conv_id
JOIN USER u ON u.user_id = cp.user_id
WHERE c.type = 'direct'
GROUP BY c.conv_id
ORDER BY c.created_at DESC;


-- 2. Show contacts and their conversation status
SELECT 
    u1.username as user,
    u2.username as contact,
    c.conv_id,
    CASE 
        WHEN c.conv_id IS NULL THEN '❌ No Conversation'
        ELSE '✅ Has Conversation'
    END as status,
    (SELECT COUNT(*) FROM MESSAGE WHERE conv_id = c.conv_id) as messages
FROM USERCONTACT uc
JOIN USER u1 ON u1.user_id = uc.user_id
JOIN USER u2 ON u2.user_id = uc.contact_user_id
LEFT JOIN CONVERSATION c ON c.created_by = LEAST(uc.user_id, uc.contact_user_id) 
    AND c.type = 'direct'
ORDER BY u1.username, u2.username;


-- 3. Summary stats
SELECT 
    'Total Users' as metric, COUNT(*) as count FROM USER
UNION ALL
SELECT 'Total Contacts in USERCONTACT', COUNT(*) FROM USERCONTACT
UNION ALL
SELECT 'Total Direct Conversations', COUNT(*) FROM CONVERSATION WHERE type = 'direct'
UNION ALL
SELECT 'Total Participants', COUNT(*) FROM CONVERSATION_PARTICIPANT
UNION ALL
SELECT 'Messages Linked to Conversations', COUNT(*) FROM MESSAGE WHERE conv_id IS NOT NULL
UNION ALL
SELECT 'Orphan Messages (no conv_id)', COUNT(*) FROM MESSAGE WHERE conv_id IS NULL;
```

---

## **What This Does:**

### **Cleanup:**
✅ Deletes ALL conversation data (fresh start)
✅ Clears conv_id from messages
✅ Removes corrupted relationships

### **Fresh Creation:**
✅ Creates ONE conversation per unique contact pair
✅ Adds EXACTLY 2 participants per conversation
✅ Links messages correctly
✅ Updates timestamps

---

## **Expected Results:**

After running this, you should see:

**For Samar:**
```
user: samar, contact: adina, conv_id: 1, status: ✅ Has Conversation
```

**For Laiba:**
```
user: laiba, contact: person1, conv_id: 2, status: ✅ Has Conversation
user: laiba, contact: person2, conv_id: 3, status: ✅ Has Conversation  
user: laiba, contact: person3, conv_id: 4, status: ✅ Has Conversation