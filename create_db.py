import sqlite3
import os

# Make sure the directory exists
if not os.path.exists('database'):
    os.makedirs('database')

# Connect to SQLite database
conn = sqlite3.connect('database/users.db')
c = conn.cursor()

# Create users table
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
''')

# Create organizations table
c.execute('''
    CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        mission TEXT,
        vision TEXT,
        status TEXT DEFAULT 'Pending'
    )
''')

# Create members table with flag_overridden column
c.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER,
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
        FOREIGN KEY (org_id) REFERENCES organizations(id)
    )
''')


# Create documents table
c.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER,
        title TEXT,
        file_path TEXT,
        tag TEXT,
        academic_year TEXT,
        FOREIGN KEY (org_id) REFERENCES organizations(id)
    )
''')

# Optional users
c.execute('INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)',
          ('sacdev_admin', 'admin123', 'sacdev'))
c.execute('INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)',
          ('rrc_user', 'rrc123', 'rrc'))

# Sample organization
c.execute('INSERT INTO organizations (name, description, mission, vision, status) VALUES (?, ?, ?, ?, ?)', 
          ('Sample Organization', 'This is a dummy organization for testing purposes.',
           'To provide an example for the student members.', 'To promote excellence and learning.',
           'Active'))
org_id = c.lastrowid

# Create students table
c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

# Add student list
all_students = [
    'John Doe', 'Jane Smith', 'Mark Johnson', 'Emily Davis', 'Chris Lee',
    'Lara Croft', 'Tony Stark', 'Bruce Wayne', 'Clark Kent', 'Diana Prince'
]

for name in all_students:
    c.execute('INSERT OR IGNORE INTO students (name) VALUES (?)', (name,))

# Add members (linked to the organization)
students = [
    ('John Doe', 'President', 'johndoe@example.com', '09171234567', 'Male', 1.9, 'CS', '4th', 'Engineering'),
    ('John Doe', 'Vice President', 'johndoe@example.com', '09171234567', 'Male', 1.9, 'CS', '4th', 'Engineering'),
    ('Jane Smith', 'Vice President', 'janesmith@example.com', '09171234568', 'Female', 3.7, 'Business', '3rd', 'Business'),
    ('Mark Johnson', 'Secretary', 'markjohnson@example.com', '09171234569', 'Male', 3.8, 'EE', '2nd', 'Engineering'),
    ('Emily Davis', 'Treasurer', 'emilydavis@example.com', '09171234570', 'Female', 3.6, 'Psychology', '1st', 'Arts'),
    ('Chris Lee', 'PRO', 'chrislee@example.com', '09171234571', 'Male', 3.9, 'ME', '4th', 'Engineering')
]

for s in students:
    c.execute('''
        INSERT INTO members (org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, *s))

conn.commit()
conn.close()

print("✅ Database and tables created successfully.")
