import sqlite3

conn = sqlite3.connect('cloudbridge.db')

# Add missing columns to files table
try:
    conn.execute("ALTER TABLE files ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0")
    print("Added is_deleted column")
except:
    print("is_deleted already exists")

try:
    conn.execute("ALTER TABLE files ADD COLUMN deleted_at DATETIME")
    print("Added deleted_at column")
except:
    print("deleted_at already exists")

conn.commit()
conn.close()
print("Migration done!")