import sqlite3
import os

# Ensure the database folder exists
os.makedirs('database', exist_ok=True)

# Connect to the database
db_path = 'database/users.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create organizations table
c.execute('''
    CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        mission TEXT,
        vision TEXT,
        status TEXT
    )
''')

# Create members table
c.execute('''
          
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER,
        full_name TEXT NOT NULL,
        position TEXT,
        email TEXT,
        contact_no TEXT,
        sex TEXT,
        qpi REAL,
        course TEXT,
        year_level TEXT,
        college TEXT,
        FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT,
        course TEXT,
        year_level TEXT,
        college TEXT
    )
''')


c.execute("DELETE FROM organizations")
c.execute("DELETE FROM members")

# Dummy data
organizations = [
    {
        'name': 'Tech Innovators',
        'description': 'A student org focused on technology and innovation.',
        'mission': 'To innovate and inspire through technology.',
        'vision': 'A future empowered by student-led tech solutions.',
        'status': 'Active',
        'members': [
            (20187650294, 'Alice Cruz', 'President', '20187650294@my.exu.edu.ph', '09170000001', 'Female', 3.6, 'Computer Science', '3rd', 'College of Engineering'),
            (20194360878, 'Ben Torres', 'Vice President', '20194360878@my.exu.edu.ph', '09170000002', 'Male', 3.4, 'Information Systems', '2nd', 'College of Engineering'),
            (20189290063, 'Cara Lim', 'Secretary', '20189290063@my.exu.edu.ph', '09170000003', 'Female', 3.8, 'Software Engineering', '4th', 'College of Engineering'),
            (20185412102, 'Dino Reyes', 'Treasurer', '20185412102@my.exu.edu.ph', '09170000004', 'Male', 3.2, 'Computer Engineering', '1st', 'College of Engineering'),
            (20183314954, 'Elaine Go', 'Auditor', '20183314954@my.exu.edu.ph', '09170000005', 'Female', 3.7, 'Information Technology', '3rd', 'College of Engineering')
        ]
    },
    {
        'name': 'Biz Leaders Guild',
        'description': 'An organization for aspiring business leaders.',
        'mission': 'To develop leadership and business acumen.',
        'vision': 'A generation of visionary entrepreneurs.',
        'status': 'Pending',
        'members': [
            (20189995919, 'Francis Uy', 'President', '20189995919@my.exu.edu.ph', '09170000006', 'Male', 3.9, 'Business Administration', '4th', 'College of Business'),
            (20194981204, 'Grace Tan', 'VP External', '20194981204@my.exu.edu.ph', '09170000007', 'Female', 3.5, 'Accounting', '2nd', 'College of Business'),
            (20195122502, 'Harold Ong', 'VP Internal', '20195122502@my.exu.edu.ph', '09170000008', 'Male', 3.6, 'Finance', '3rd', 'College of Business'),
            (20183595243, 'Isabelle Chua', 'Secretary', '20183595243@my.exu.edu.ph', '09170000009', 'Female', 3.3, 'Marketing', '1st', 'College of Business'),
            (20187361430, 'Jake Yu', 'PRO', '20187361430@my.exu.edu.ph', '09170000010', 'Male', 3.4, 'Entrepreneurship', '2nd', 'College of Business')
        ]
    },
    {
        'name': 'Arts & Culture Circle',
        'description': 'Celebrating arts, heritage, and creative expression.',
        'mission': 'To enrich the university through the arts.',
        'vision': 'A vibrant cultural community of students.',
        'status': 'Active',
        'members': [
            (20189168074, 'Kyla Santos', 'President', '20189168074@my.exu.edu.ph', '09170000011', 'Female', 3.8, 'Fine Arts', '4th', 'College of Arts and Sciences'),
            (20195244592, 'Leo Bautista', 'VP Cultural Affairs', '20195244592@my.exu.edu.ph', '09170000012', 'Male', 3.2, 'Performing Arts', '3rd', 'College of Arts and Sciences'),
            (20183826842, 'Mara Diaz', 'Secretary', '20183826842@my.exu.edu.ph', '09170000013', 'Female', 3.6, 'Literature', '2nd', 'College of Arts and Sciences'),
            (20187347240, 'Nico Ramos', 'Treasurer', '20187347240@my.exu.edu.ph', '09170000014', 'Male', 3.3, 'Media Arts', '1st', 'College of Arts and Sciences'),
            (20183686866, 'Olive Velasco', 'Curator', '20183686866@my.exu.edu.ph', '09170000015', 'Female', 3.9, 'Art History', '3rd', 'College of Arts and Sciences')
        ]
    },
    {
        'name': 'ORGless',
        'description': 'Students without organizations.',
        'mission': 'To list students who are not part of any organization.',
        'vision': 'Home for the orgless',
        'status': 'Active',
        'members': [
            (20009990000, 'John Doe', 'Forever President', '20009990000@my.xu.edu.ph', ' 09876543210','Unknown', 0.0, 'Unknown', 'Unknown', 'Unknown'), 
            ]
    }
]




# Insert organizations and their members
for org in organizations:
    c.execute('''
        INSERT INTO organizations (name, description, mission, vision, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (org['name'], org['description'], org['mission'], org['vision'], org['status']))
    
    org_id = c.lastrowid  # Get the ID of the organization just inserted
    
    for member in org['members']:
        c.execute('''
            INSERT INTO members (
                id, org_id, full_name, position, email, contact_no,
                sex, qpi, course, year_level, college
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*member[:1], org_id, *member[1:]))

# Finalize changes and close connection
conn.commit()
conn.close()

print("✅ Successfully created and populated the database with 3 organizations and 15 members.")
