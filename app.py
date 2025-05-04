from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret123'  # Required for session and flash

DATABASE = 'database/users.db'

# --- DATABASE CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect('database/users.db')
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
            return 'Invalid credentials'

    return render_template('login.html')


# --- DASHBOARD ROUTE ---
@app.route('/sacdev_dashboard')
def sacdev_dashboard():
    if session.get('role') != 'sacdev':
        return redirect('/login')

    conn = sqlite3.connect('database/users.db')
    c = conn.cursor()
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
    session.clear()
    return redirect(url_for('login'))

# --- ORGANIZATIONS ---

@app.route('/organization/<int:org_id>')
def view_organization(org_id):
    db = get_db()
    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    members = db.execute('SELECT * FROM members WHERE org_id = ?', (org_id,)).fetchall()
    documents = db.execute('SELECT * FROM documents WHERE org_id = ?', (org_id,)).fetchall()
    return render_template('organization_view.html', org=org, members=members, documents=documents)





if __name__ == '__main__':
    app.run(debug=True)
