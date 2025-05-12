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

# Create members table
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

# Optional: Insert default admin/SACDEV user
c.execute('''
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES (?, ?, ?)
''', ('sacdev_admin', 'admin123', 'sacdev'))

# Optional: Insert default RRC user
c.execute('''
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES (?, ?, ?)
''', ('rrc_user', 'rrc123', 'rrc'))

# Optional: Insert a sample organization
c.execute('''
    INSERT INTO organizations (name, description, mission, vision, status)
    VALUES (?, ?, ?, ?, ?)
''', ('Sample Organization', 'This is a dummy organization for testing purposes.', 
      'To provide an example for the student members.', 'To promote excellence and learning.',
      'Active'))

# Get the ID of the inserted organization
org_id = c.lastrowid

# Create students table
c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
''')

# Insert all students (some will be members, others will remain orgless)
all_students = [
    'John Doe', 'Jane Smith', 'Mark Johnson', 'Emily Davis', 'Chris Lee',
    'Lara Croft', 'Tony Stark', 'Bruce Wayne', 'Clark Kent', 'Diana Prince'
]

for name in all_students:
    c.execute('INSERT OR IGNORE INTO students (name) VALUES (?)', (name,))


# Insert 5 dummy students (members)
students = [
    ('John Doe', 'President', 'johndoe@example.com', '09171234567', 'Male', 3.5, 'Computer Science', '4th', 'College of Engineering'),
    ('Jane Smith', 'Vice President', 'janesmith@example.com', '09171234568', 'Female', 3.7, 'Business Administration', '3rd', 'College of Business'),
    ('Mark Johnson', 'Secretary', 'markjohnson@example.com', '09171234569', 'Male', 3.8, 'Electrical Engineering', '2nd', 'College of Engineering'),
    ('Emily Davis', 'Treasurer', 'emilydavis@example.com', '09171234570', 'Female', 3.6, 'Psychology', '1st', 'College of Arts and Sciences'),
    ('Chris Lee', 'Public Relations Officer', 'chrislee@example.com', '09171234571', 'Male', 3.9, 'Mechanical Engineering', '4th', 'College of Engineering')
]

# Insert each student into the 'members' table
for student in students:
    c.execute('''
        INSERT INTO members (org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, student[0], student[1], student[2], student[3], student[4], student[5], student[6], student[7], student[8]))

conn.commit()
conn.close()

print("✅ Database and tables created successfully.")