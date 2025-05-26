from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_login import logout_user
import sqlite3
import traceback

app = Flask(__name__)
app.secret_key = 'secret123'  # Required for session and flash

DATABASE = 'database/users.db'

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

    # Delete organization
    if request.method == 'POST' and 'delete_org' in request.form:
        org_id = request.form['org_id']
        c.execute('UPDATE members SET org_id = NULL WHERE org_id = ?', (org_id,))
        c.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        conn.commit()

    # Ensure default org exists
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

    # Assign orgless members to "No Organization"
    c.execute('SELECT * FROM members WHERE org_id IS NULL')
    orgless_members = c.fetchall()
    for member in orgless_members:
        c.execute('UPDATE members SET org_id = ? WHERE id = ?', (default_org_id, member['id']))
        conn.commit()

    # Fetch all organizations and their member counts
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', '').lower()

    query = '''
    SELECT o.*, COUNT(m.id) AS member_count
    FROM organizations o
    LEFT JOIN members m ON o.id = m.org_id
'''
    params = []

    if search:
        query += ' WHERE o.name LIKE ? OR o.description LIKE ?'
        params.extend([f'%{search}%', f'%{search}%'])

    # Grouping
    query += ' GROUP BY o.id'

# Sorting logic
    if sort == 'name':
        query += ' ORDER BY o.name COLLATE NOCASE ASC'
    elif sort in ['active', 'pending', 'inactive']:
        query += ' ORDER BY (o.status = ?) DESC, o.name ASC'
        params.append(sort.capitalize())

# ⬇️ Always execute the final query, regardless of which branch ran
    c.execute(query, params)
    orgs = c.fetchall()

# ⬇️ And return from the function here
    return render_template('sacdev_dashboard.html', user=session['username'], orgs=orgs)

@app.route('/add_organization', methods=['POST'])
def add_organization():
    if session.get('role') != 'sacdev':
        return redirect('/login')

    name = request.form['name']
    description = request.form['description']
    mission = request.form['mission']
    vision = request.form['vision']
    status = request.form['status']

    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO organizations (name, description, mission, vision, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, description, mission, vision, status))
    conn.commit()
    conn.close()

    return redirect('/sacdev_dashboard')


@app.route('/add_organization_form', methods=['GET'])
def add_organization_form():
    if session.get('role') != 'sacdev':
        return redirect('/login')
    return render_template('add_organization.html')


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
    c = db.cursor()
    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

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

            c.execute(
                '''INSERT INTO members (
                    org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
            )
            conn.commit()


        elif 'kick_member' in request.form:
            try:
                # --- Ensure default org exists ---
                c.execute("SELECT * FROM organizations WHERE name = 'No Organization'")
                default_org = c.fetchone()
                default_org_id = default_org['id']
                print(f"Default Org ID: {default_org_id}")
                member_id = request.form['member_id']
                c.execute('UPDATE members SET org_id = ? WHERE id = ?', (default_org_id, member_id))
                conn.commit()
            
            except Exception as e:
                print(f"Error: {e}")

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
    search_query = request.args.get('search', '').strip()
    try:
        conn = sqlite3.connect('database/users.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if search_query:
            c.execute('''
                SELECT o.name AS org_name, m.*
                FROM members m
                JOIN organizations o ON m.org_id = o.id
                WHERE m.full_name LIKE ? OR o.name LIKE ?
            ''', ('%' + search_query + '%', '%' + search_query + '%'))
        else:
            c.execute('''
                SELECT o.name AS org_name, m.*
                FROM members m
                JOIN organizations o ON m.org_id = o.id
            ''')

        students = c.fetchall()
        conn.close()

        return render_template('students_orgs.html', students=students, search_query=search_query)

    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>"


@app.route('/organization_list', methods=['GET'])
def organization_list():
    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    search_query = request.args.get('search', '').strip()

    if search_query:
        c.execute("SELECT * FROM organizations WHERE name LIKE ? ORDER BY name ASC", ('%' + search_query + '%',))
    else:
        c.execute("SELECT * FROM organizations ORDER BY name ASC")

    orgs = c.fetchall()
    conn.close()
    return render_template('organization_list.html', orgs=orgs, search_query=search_query)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)