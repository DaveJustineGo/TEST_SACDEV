from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_login import logout_user
import logging
import os
from logging.handlers import RotatingFileHandler
import sqlite3
import traceback

app = Flask(__name__)
app.secret_key = 'secret123'  # Required for session and flash

DATABASE = 'database/users.db'

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure file handler
file_handler = RotatingFileHandler('logs/flask_app.log', maxBytes=10240, backupCount=5)
file_handler.setLevel(logging.INFO)

# Log format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to Flask's logger
if not app.logger.handlers:
    app.logger.addHandler(file_handler)

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

    c.execute('SELECT * FROM organizations')
    orgs = c.fetchall()
    conn.close()

    return render_template('sacdev_dashboard.html', user=session['username'], orgs=orgs)


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
            db.execute('''
                UPDATE members
                SET org_id = (SELECT id FROM organizations WHERE name = 'ORGless'),
                    position = 'member'
                WHERE id = ?
                       
            ''', ( member_id,))
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
    app.run(debug=True,host='0.0.0.0', port=5000)
