from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_login import logout_user
import sqlite3
import traceback
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'  # Required for session and flash

DATABASE = 'database/users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, timeout=10)
        db.row_factory = sqlite3.Row
    return db

def log_change(action, table_name, record_id, changes, changed_by, conn=None):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DATABASE, timeout=10)
        close_conn = True

    c = conn.cursor()
    c.execute('''
        INSERT INTO changelog (action, table_name, record_id, changes, changed_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        action,
        table_name,
        record_id,
        json.dumps(changes),
        changed_by
    ))
    if close_conn:
        conn.commit()
        conn.close()

@app.route('/revert_change/<int:log_id>', methods=['POST'])
def revert_change(log_id):
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    conn = get_db()
    c = conn.cursor()

    # Fetch the log entry
    c.execute('SELECT * FROM changelog WHERE id = ?', (log_id,))
    log_entry = c.fetchone()

    if not log_entry:
        flash('Log entry not found.', 'error')
        return redirect(url_for('changelog'))

    table = log_entry['table_name']
    record_id = log_entry['record_id']
    changes = json.loads(log_entry['changes'])
    action = log_entry['action']

    try:
        if table == 'members':
            if 'Manually flagged' in changes.get('message', ''):
                # Revert manual flag
                c.execute('''
                    UPDATE members
                    SET manually_flagged = 0,
                        manual_flag_reason = NULL
                    WHERE id = ?
                ''', (record_id,))
                revert_message = 'Manual flag reverted'

            elif 'Manual flag removed' in changes.get('message', ''):
                # Re-apply manual flag
                reason = changes.get('reason', 'Restored reason')
                c.execute('''
                    UPDATE members
                    SET manually_flagged = 1,
                        manual_flag_reason = ?
                    WHERE id = ?
                ''', (reason, record_id))
                revert_message = 'Manual flag restored'

            elif 'Toggled override' in changes.get('message', ''):
                # Re-toggle override
                c.execute('''
                    UPDATE members
                    SET flag_overridden = CASE flag_overridden WHEN 1 THEN 0 ELSE 1 END
                    WHERE id = ?
                ''', (record_id,))
                revert_message = 'Override flag toggled back'

            else:
                flash('⚠️ Revert not supported for this member change.', 'error')
                return redirect(url_for('changelog'))

            # Prevent redundant "Reverted:" in message
            original_msg = changes.get('message', '')
            if original_msg.lower().startswith("reverted:"):
                original_msg = original_msg[9:].strip()

            log_change(
                'REVERT',
                table,
                record_id,
                {
                    'message': f"Reverted: {original_msg}"
                },
                session.get('username', 'unknown'),
                conn
            )

            conn.commit()
            flash(f'✅ {revert_message} for record ID {record_id}', 'success')

        else:
            flash('⚠️ Revert not yet supported for this table.', 'error')

    except Exception as e:
        print(f"Error in revert: {e}")
        flash('⚠️ Failed to revert change.', 'error')

    return redirect(url_for('changelog'))





@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/changelog')
def changelog():
    conn = get_db()
    c = conn.cursor()

    table_filter = request.args.get('table')
    action_filter = request.args.get('action')
    user_filter = request.args.get('user')
    sort = request.args.get('sort', 'timestamp_desc')

    # Build WHERE clauses
    conditions = []
    values = []

    if table_filter:
        conditions.append("table_name = ?")
        values.append(table_filter)

    if action_filter:
        conditions.append("action = ?")
        values.append(action_filter)

    if user_filter:
        conditions.append("changed_by LIKE ?")
        values.append(f"%{user_filter}%")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Sorting
    sort_clause = "ORDER BY timestamp DESC"
    if sort == "timestamp_asc":
        sort_clause = "ORDER BY timestamp ASC"

    query = f"SELECT * FROM changelog {where_clause} {sort_clause}"
    c.execute(query, values)
    logs_raw = c.fetchall()

    logs = []
    for log in logs_raw:
        try:
            changes = json.loads(log['changes'])
        except Exception:
            changes = {"message": log['changes']}
        logs.append({
            "id": log["id"],
            "timestamp": log["timestamp"],
            "changed_by": log["changed_by"],
            "action": log["action"],
            "table_name": log["table_name"],
            "record_id": log["record_id"],
            "changes": changes
        })

    return render_template('changelog.html', logs=logs)

@app.route('/clear_changelog', methods=['POST'])
def clear_changelog():
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    conn = get_db()
    c = conn.cursor()

    table = request.form.get('table')
    action = request.form.get('action')
    user = request.form.get('user')

    conditions = []
    values = []

    if table:
        conditions.append("table_name = ?")
        values.append(table)
    if action:
        conditions.append("action = ?")
        values.append(action)
    if user:
        conditions.append("changed_by LIKE ?")
        values.append(f"%{user}%")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    delete_query = f"DELETE FROM changelog {where_clause}"
    c.execute(delete_query, values)
    conn.commit()

    flash("🗑️ Changelog entries matching your filter have been deleted.", "success")
    return redirect(url_for('changelog'))


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

    conn = get_db()
    c = conn.cursor()

    # Delete organization
    if request.method == 'POST' and 'delete_org' in request.form:
        org_id = request.form['org_id']

        # Fetch organization data before deleting
        c.execute('SELECT * FROM organizations WHERE id = ?', (org_id,))
        org_data = c.fetchone()

        # Ensure "No Organization" exists
        c.execute("SELECT id FROM organizations WHERE name = 'No Organization'")
        no_org = c.fetchone()
        no_org_id = no_org['id'] if no_org else None

        if no_org_id:
    # Only reassign members who belong ONLY to this org
            c.execute('''
             UPDATE members
            SET org_id = ?, position = 'Student'
            WHERE org_id = ? AND student_id NOT IN (
            SELECT student_id FROM members WHERE org_id != ?
        )
    ''', (no_org_id, org_id, org_id))


        # Delete the organization
        c.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        conn.commit()

        # Log the change
        log_change(
            'DELETE',
            'organizations',
            org_id,
            dict(org_data) if org_data else {},
            session.get('username', 'unknown'),
            conn
        )

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

    query += ' GROUP BY o.id'

    if sort == 'name':
        query += ' ORDER BY o.name COLLATE NOCASE ASC'
    elif sort in ['active', 'pending', 'inactive']:
        query += ' ORDER BY (o.status = ?) DESC, o.name ASC'
        params.append(sort.capitalize())

    c.execute(query, params)
    orgs = c.fetchall()

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

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO organizations (name, description, mission, vision, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, description, mission, vision, status))
    conn.commit()
    org_id = c.lastrowid

    log_change(
        'ADD',
        'organizations',
        org_id,
        {
            'name': name,
            'description': description,
            'mission': mission,
            'vision': vision,
            'status': status
        },
        session.get('username', 'unknown'),
        conn
    )

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
    return render_template('rrc_dashboard.html', user=session['username'])

# --- LOGOUT ---
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

# --- ORGANIZATIONS ---
@app.route('/organization/<int:org_id>', methods=['GET', 'POST'])
def view_organization(org_id):
    conn = get_db()
    c = conn.cursor()

    if request.method == 'POST':
        if 'add_member' in request.form:
            student_id = request.form['student_id']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            full_name = f"{first_name} {last_name}"

            position = request.form['position']
            email = request.form['email']
            contact_no = request.form['contact_no']
            sex = request.form['sex']
            qpi = request.form['qpi']
            course = request.form['course']
            year_level = request.form['year_level']
            college = request.form['college']

            # Check if member already exists in this organization
            c.execute(
                'SELECT * FROM members WHERE student_id = ? AND org_id = ?',
                (student_id, org_id)
            )
            if c.fetchone():
                flash(f"⚠️ Student {full_name} already exists in this organization!", "error")
            else:
                c.execute('''
                    INSERT INTO members (student_id, org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (student_id, org_id, full_name, position, email, contact_no, sex, qpi, course, year_level, college))
                conn.commit()

                try:
                    log_change(
                        'ADD',
                        'members',
                        student_id,
                        {
                            'message': f"Added member {full_name} to organization ID {org_id}",
                            'details': {
                                'org_id': org_id,
                                'full_name': full_name,
                                'position': position,
                                'email': email,
                                'contact_no': contact_no,
                                'sex': sex,
                                'qpi': qpi,
                                'course': course,
                                'year_level': year_level,
                                'college': college
                            }
                        },
                        session.get('username', 'unknown'),
                        conn
                    )
                except Exception as log_err:
                    print(f"Error in log_change (add_member): {log_err}")

        elif 'kick_member' in request.form:
            try:
                # Get No Organization ID
                c.execute("SELECT id FROM organizations WHERE name = 'No Organization'")
                no_org = c.fetchone()
                no_org_id = no_org['id'] if no_org else None

                if not no_org_id:
                    flash("⚠️ 'No Organization' not found in database.", "error")
                    return redirect(url_for('view_organization', org_id=org_id))

                member_id = request.form['member_id']

                # Fetch member's record
                c.execute("SELECT * FROM members WHERE id = ?", (member_id,))
                member_data = c.fetchone()

                if not member_data:
                    flash("⚠️ Member not found.", "error")
                    return redirect(url_for('view_organization', org_id=org_id))

                student_id = member_data['student_id']
                previous_org_id = member_data['org_id']

                # Count other organizations (excluding this org and No Organization)
                c.execute('''
                SELECT COUNT(*) AS other_orgs
                FROM members
                WHERE student_id = ? AND org_id NOT IN (?, ?)
                ''', (student_id, org_id, no_org_id))
                org_row = c.fetchone()
                org_count = org_row['other_orgs'] if org_row and 'other_orgs' in org_row.keys() else 0


                if org_count == 0:
                    # Reassign to No Organization if no other orgs
                    c.execute('''
                        UPDATE members
                        SET org_id = ?, position = 'Student'
                        WHERE id = ?
                    ''', (no_org_id, member_id))
                    log_message = f"Kicked member {member_data['full_name']} from org {previous_org_id} → No Organization"
                else:
                    # Remove this member record if they have other orgs
                    c.execute('DELETE FROM members WHERE id = ?', (member_id,))
                    log_message = f"Removed member {member_data['full_name']} from org {previous_org_id} (still in other orgs)"

                conn.commit()

                log_change(
                    'UPDATE' if org_count == 0 else 'DELETE',
                    'members',
                    member_id,
                    {
                        'message': log_message,
                        'details': {
                            'student_id': student_id,
                            'previous_org_id': previous_org_id,
                            'new_org_id': no_org_id if org_count == 0 else "Other Organizations"
                        }
                    },
                    session.get('username', 'unknown'),
                    conn
                )

            except Exception as e:
                print(f"Error during kick_member: {e}")
                flash("⚠️ Failed to kick member due to internal error.", "error")

        return redirect(url_for('view_organization', org_id=org_id))

    # Always fetch organization and related data
    org = c.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()

    members = c.execute('''
        SELECT position, full_name, sex AS gender, qpi, id
        FROM members
        WHERE org_id = ?
    ''', (org_id,)).fetchall()

    documents = c.execute('SELECT * FROM documents WHERE org_id = ?', (org_id,)).fetchall()

    total_members = len(members)
    male_count = sum(1 for m in members if m['gender'] == 'Male')
    female_count = sum(1 for m in members if m['gender'] == 'Female')

    return render_template(
        'organization_view.html',
        org=org,
        members=members,
        documents=documents,
        total_members=total_members,
        male_count=male_count,
        female_count=female_count
    )


# --- STUDENTS ORGS ---
MAJOR_POSITIONS = {'President', 'Vice President', 'Chair', 'Secretary', 'Treasurer'}

@app.route('/students_orgs')
def students_orgs():
    search_query = request.args.get('search', '').strip().lower()

    conn = get_db()
    c = conn.cursor()
    c.execute('''
    SELECT m.*, o.name AS org_name
    FROM members m
    JOIN organizations o ON m.org_id = o.id
    ''')
    rows = c.fetchall()

    students = {}
    for r in rows:
        name = r['full_name']

        if name not in students:
            students[name] = {
                'id': r['id'],
                'full_name': name,
                'qpi': r['qpi'],
                'positions': [],
                'orgs': [],
                'flag': False,
                'flag_reasons': [],
                'overridden': bool(r['flag_overridden']),
                'manually_flagged': bool(r['manually_flagged']),
                'manual_reason': r['manual_flag_reason'],
                'email': r['email'],
                'contact_no': r['contact_no'],
                'sex': r['sex'],
                'course': r['course'],
                'year_level': r['year_level'],
                'college': r['college']
            }

        students[name]['positions'].append(r['position'])
        students[name]['orgs'].append(r['org_name'])

    for student in students.values():
        major_count = sum(1 for pos in student['positions'] if pos in MAJOR_POSITIONS)
        low_qpi = float(student['qpi']) < 2.0

        reasons = []
        if major_count > 1:
            reasons.append("Multiple major positions")
        if low_qpi:
            reasons.append("QPI below 2.0")

        student['auto_flag'] = bool(reasons) and not student['overridden']
        student['flag_reasons'] = reasons
        student['flag'] = student['auto_flag'] or student['manually_flagged']

    def matches_search(student, query):
        name_parts = student['full_name'].lower().split()
        orgs = [org.lower() for org in student['orgs']]
        return (
            query in student['full_name'].lower()
            or any(query in part for part in name_parts)
            or any(query in org for org in orgs)
        )

    if search_query:
        students = {
            name: s for name, s in students.items()
            if matches_search(s, search_query)
        }

    return render_template('students_orgs.html', students=students.values(), search_query=search_query)

@app.route('/override_flag', methods=['POST'])
def override_flag():
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    member_id = request.form['member_id']
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE members SET flag_overridden = 1 WHERE id = ?', (member_id,))
    conn.commit()

    return redirect(url_for('students_orgs'))

@app.route('/toggle_override_flag', methods=['POST'])
def toggle_override_flag():
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    member_id = int(request.form['member_id'])
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE members
        SET flag_overridden = CASE flag_overridden WHEN 1 THEN 0 ELSE 1 END
        WHERE id = ?
    ''', (member_id,))
    

    log_change(
        'UPDATE',
        'members',
        member_id,
        {
            'message': f'Toggled override flag for member ID {member_id}'
        },
        session.get('username', 'unknown'),
        conn
    )
    conn.commit()
    return redirect(url_for('students_orgs'))

@app.route('/manual_flag', methods=['POST'])
def manual_flag():
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    member_id = int(request.form['member_id'])
    reason = request.form['manual_reason']

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE members
        SET manually_flagged = 1,
            manual_flag_reason = ?
        WHERE id = ?
    ''', (reason, member_id))
    

    log_change(
        'UPDATE',
        'members',
        member_id,
        {
            'message': f'Manually flagged member ID {member_id}',
            'reason': reason
        },  
        session.get('username', 'unknown'),
        conn
    )
    conn.commit()
    return redirect(url_for('students_orgs'))

@app.route('/manual_unflag', methods=['POST'])
def manual_unflag():
    if session.get('role') != 'sacdev':
        return 'Unauthorized', 403

    member_id = int(request.form['member_id'])

    conn = get_db()
    c = conn.cursor()

    # Get the current reason before unflagging
    c.execute('SELECT manual_flag_reason FROM members WHERE id = ?', (member_id,))
    row = c.fetchone()
    reason = row['manual_flag_reason'] if row else None

    # Clear the flag
    c.execute('''
        UPDATE members
        SET manually_flagged = 0,
            manual_flag_reason = NULL
        WHERE id = ?
    ''', (member_id,))

    log_change(
        'UPDATE',
        'members',
        member_id,
        {
            'message': f'Manual flag removed from member ID {member_id}',
            'reason': reason
        },
        session.get('username', 'unknown'),
        conn
    )

    conn.commit()
    return redirect(url_for('students_orgs'))



@app.route('/organization_list', methods=['GET'])
def organization_list():
    conn = get_db()
    c = conn.cursor()

    search_query = request.args.get('search', '').strip()

    if search_query:
        c.execute("SELECT * FROM organizations WHERE name LIKE ? ORDER BY name ASC", ('%' + search_query + '%',))
    else:
        c.execute("SELECT * FROM organizations ORDER BY name ASC")

    orgs = c.fetchall()

    return render_template('organization_list.html', orgs=orgs, search_query=search_query)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
