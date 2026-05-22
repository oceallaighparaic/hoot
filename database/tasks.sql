PRAGMA foreign_keys = ON
;

DROP TABLE IF EXISTS users
;
DROP TABLE IF EXISTS friends
;
DROP TABLE IF EXISTS permissions
;
DROP TABLE IF EXISTS messages
;

CREATE TABLE permissions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL UNIQUE
)
;
-- SEED
INSERT INTO permissions(name)
VALUES ('user'),('admin')
;

CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    permission_id INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE SET DEFAULT
)
;
-- SEED
INSERT INTO users(username, password, permission_id)
VALUES (
    'ADMIN', 
    'scrypt:32768:8:1$v6YzVtdQ6HawdJfR$5ab41d01354b777aead5ed68ca5d9fc71db37cb32b724b85463901b85f85c568d23fc59ec08f1c8d9fae7eaf77fd1e93d0a1d1f1a586bd578cf7322d7565543f', 
    2
)
;

CREATE TABLE friends(
    user1 INTEGER NOT NULL,
    user2 INTEGER NOT NULL,
    UNIQUE(user1,user2),
    FOREIGN KEY (user1) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user2) REFERENCES users(id) ON DELETE CASCADE
)
;

CREATE TABLE messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message VARCHAR NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (sender_id <> recipient_id)
)
;