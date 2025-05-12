from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_login import logout_user
import sqlite3
import traceback

app = Flask(__name__)
app.secret_key = 'secret123'  # Required for session and flash

DATABASE = 'database/users.db'

# --- DATABASE CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect('database/db_script.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- LOGIN ROUTE ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                          (username, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] == 'sacdev':
                return redirect(url_for('sacdev_dashboard'))
            elif user['role'] == 'rrc':
                return redirect(url_for('rrc_dashboard'))
            else:
                return 'Unauthorized', 403
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


# --- DASHBOARD ROUTE ---
@app.route('/sacdev_dashboard', methods=['GET', 'POST'])
def sacdev_dashboard():
    if session.get('role') != 'sacdev':
        return redirect('/login')

    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Add organization
    if request.method == 'POST':
        if 'add_org' in request.form:
            name = request.form['name']
            description = request.form['description']
            mission = request.form['mission']
            vision = request.form['vision']
            status = request.form['status']
            c.execute('INSERT INTO organizations (name, description, mission, vision, status) VALUES (?, ?, ?, ?, ?)',
                      (name, description, mission, vision, status))
            conn.commit()
        elif 'delete_org' in request.form:
            org_id = request.form['org_id']
            c.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
            conn.commit()

    # --- Ensure default org exists ---
    c.execute("SELECT * FROM organizations WHERE name = 'No Organization'")
    default_org = c.fetchone()

    if not default_org:
        c.execute('''
            INSERT INTO organizations (name, description, mission, vision, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('No Organization', 'Auto-assigned orgless students', '', '', 'Active'))
        conn.commit()
        c.execute("SELECT * FROM organizations WHERE name = 'No Organization'")
        default_org = c.fetchone()

    default_org_id = default_org['id']

    # --- Find orgless students in 'members' table ---
    c.execute('SELECT id, name FROM students')  # Assuming you have a students table
    all_students = c.fetchall()

    c.execute('SELECT full_name FROM members')
    members = c.fetchall()
    member_names = {m['full_name'] for m in members}

    # --- Insert orgless students into default org ---
    for student in all_students:
        if student['name'] not in member_names:
            c.execute('''
                INSERT INTO members (org_id, full_name)
                VALUES (?, ?)
            ''', (default_org_id, student['name']))
    conn.commit()

    # --- Fetch orgs with member counts ---
    c.execute('''
        SELECT o.*, COUNT(m.id) AS member_count
        FROM organizations o
        LEFT JOIN members m ON o.id = m.org_id
        GROUP BY o.id
    ''')
    orgs = c.fetchall()

    # --- Orgless students (optional: those in default org) ---
    c.execute('''
        SELECT name FROM students
        WHERE name NOT IN (
            SELECT full_name FROM members WHERE org_id != ?
        )
    ''', (default_org_id,))
    orgless_students = c.fetchall()

    conn.close()

    return render_template('sacdev_dashboard.html', user=session['username'], orgs=orgs, orgless_students=orgless_students)


@app.route('/rrc_dashboard')
def rrc_dashboard():
    if 'username' not in session or session.get('role') != 'rrc':
        return redirect(url_for('login'))
    
    # You can customize what data RRC should see here
    return render_template('rrc_dashboard.html', user=session['username'])

# --- LOGOUT ---
@app.route('/logout')
def logout():
    # logout_user()  
    return redirect(url_for('login'))  

# --- ORGANIZATIONS ---
@app.route('/organization/<int:org_id>', methods=['GET', 'POST'])
def view_organization(org_id):
    db = get_db()

    # Add new member manually by entering details
    if request.method == 'POST':
        if 'add_member' in request.form:
            full_name = request.form['full_name']
            position = request.form['position']
            email = request.form['email']
            contact_no = request.form['contact_no']
            sex = request.form['sex']
            qpi = request.form['qpi']
            course = request.form['course']
            year_level = request.form['year_level']
            college = request.form['college']

            db.execute(
                '''INSERT INTO members (
                    org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
            )
            db.commit()

        elif 'kick_member' in request.form:
            member_id = request.form['member_id']
            db.execute('DELETE FROM members WHERE id = ?', (member_id,))
            db.commit()

        return redirect(url_for('view_organization', org_id=org_id))

    # Fetch organization details
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()

    # Fetch members (no join needed)
    members = db.execute('''
        SELECT position, full_name, sex AS gender, qpi, id
        FROM members
        WHERE org_id = ?
    ''', (org_id,)).fetchall()

    # Optional: documents table
    documents = db.execute('SELECT * FROM documents WHERE org_id = ?', (org_id,)).fetchall()

    # Count members
    total_members = len(members)
    male_count = sum(1 for m in members if m['gender'] == 'Male')
    female_count = sum(1 for m in members if m['gender'] == 'Female')

    return render_template('organization_view.html',
                           org=org,
                           members=members,
                           documents=documents,
                           total_members=total_members,
                           male_count=male_count,
                           female_count=female_count)

# ---STUDENTS ORGS--- 
@app.route('/students_orgs')
def students_orgs():
    try:
        conn = sqlite3.connect('database/users.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT o.name AS org_name, m.*
            FROM members m
            JOIN organizations o ON m.org_id = o.id
        ''')

        students = c.fetchall()
        conn.close()

        return render_template('students_orgs.html', students=students)

    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>"


if __name__ == '__main__':
    app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)