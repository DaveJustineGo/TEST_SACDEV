import sqlite3
import os

# Ensure database directory exists
if not os.path.exists('database'):
    os.makedirs('database')

# Delete old database for clean setup (optional: remove if preserving data)
db_path = 'database/users.db'
if os.path.exists(db_path):
    os.remove(db_path)

# Connect to SQLite database
conn = sqlite3.connect(db_path)
c = conn.cursor()

# --- DROP TABLES (only needed if not deleting db file above) ---
# Uncomment below if you don't delete the DB file
# c.execute('DROP TABLE IF EXISTS members')
# c.execute('DROP TABLE IF EXISTS users')
# c.execute('DROP TABLE IF EXISTS changelog')
# c.execute('DROP TABLE IF EXISTS organizations')
# c.execute('DROP TABLE IF EXISTS documents')
# c.execute('DROP TABLE IF EXISTS students')

# --- USERS TABLE ---
c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
''')

# --- CHANGELOG TABLE ---
c.execute('''
    CREATE TABLE changelog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER NOT NULL,
        changes TEXT NOT NULL,
        changed_by TEXT NOT NULL,
        timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
    )
''')

# --- ORGANIZATIONS TABLE ---
c.execute('''
    CREATE TABLE organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        mission TEXT,
        vision TEXT,
        status TEXT DEFAULT 'Pending'
    )
''')

# --- MEMBERS TABLE ---
c.execute('''
    CREATE TABLE members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        org_id INTEGER NOT NULL,
        full_name TEXT,
        position TEXT,
        email TEXT,
        contact_no TEXT,
        sex TEXT,
        qpi REAL,
        course TEXT,
        year_level TEXT,
        college TEXT,
        flag_overridden INTEGER DEFAULT 0,
        manually_flagged INTEGER DEFAULT 0,
        manual_flag_reason TEXT,
        FOREIGN KEY (org_id) REFERENCES organizations(id),
        UNIQUE (student_id, org_id)
    )
''')

# --- DOCUMENTS TABLE ---
c.execute('''
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER,
        title TEXT,
        file_path TEXT,
        tag TEXT,
        academic_year TEXT,
        FOREIGN KEY (org_id) REFERENCES organizations(id)
    )
''')

# --- STUDENTS TABLE ---
c.execute('''
    CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

# --- INSERT DEFAULT USERS ---
c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('sacdev_admin', 'admin123', 'sacdev'))
c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('rrc_user', 'rrc123', 'rrc'))

# --- INSERT "No Organization" (used for kicks) ---
c.execute('''
    INSERT INTO organizations (name, description, mission, vision, status)
    VALUES (?, ?, ?, ?, ?)
''', ('No Organization', 'Auto-assigned orgless students', '', '', 'Active'))
no_org_id = c.lastrowid

# --- INSERT Sample Organization ---
c.execute('''
    INSERT INTO organizations (name, description, mission, vision, status)
    VALUES (?, ?, ?, ?, ?)
''', ('Sample Organization',
      'This is a dummy organization for testing purposes.',
      'To provide an example for the student members.',
      'To promote excellence and learning.',
      'Active'))
sample_org_id = c.lastrowid

# --- INSERT Students ---
all_students = [
    'John Doe', 'Jane Smith', 'Mark Johnson', 'Emily Davis', 'Chris Lee',
    'Lara Croft', 'Tony Stark', 'Bruce Wayne', 'Clark Kent', 'Diana Prince'
]
for name in all_students:
    c.execute('INSERT INTO students (name) VALUES (?)', (name,))

# Fetch student IDs and map them correctly
c.execute('SELECT id, name FROM students')
student_records = c.fetchall()
name_to_id = {name: sid for sid, name in student_records}

# --- INSERT Members into Sample Organization ---
members = [
    ('John Doe', 'President', 'johndoe@example.com', '09171234567', 'Male', 1.9, 'CS', '4th', 'Engineering'),
    ('Jane Smith', 'Vice President', 'janesmith@example.com', '09171234568', 'Female', 3.7, 'Business', '3rd', 'Business'),
    ('Mark Johnson', 'Secretary', 'markjohnson@example.com', '09171234569', 'Male', 3.8, 'EE', '2nd', 'Engineering'),
    ('Emily Davis', 'Treasurer', 'emilydavis@example.com', '09171234570', 'Female', 3.6, 'Psychology', '1st', 'Arts'),
    ('Chris Lee', 'PRO', 'chrislee@example.com', '09171234571', 'Male', 3.9, 'ME', '4th', 'Engineering')
]

for m in members:
    student_name = m[0]
    student_id = name_to_id.get(student_name)
    if student_id:
        c.execute('''
            INSERT INTO members (student_id, org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, sample_org_id, *m))

# --- Done ---
conn.commit()
conn.close()

print("✅ Database and tables created/reset successfully.")
