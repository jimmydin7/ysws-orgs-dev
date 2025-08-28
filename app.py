from flask import Flask, render_template, request, redirect, url_for, session
from config import SECRET_KEY, KEYS_FILE, USERS_FILE
from utils import load_json_file, save_json_file, login_required
from tools.ysws_catalog import generate_yml
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/", methods=['GET', 'POST'])
@login_required
def main():
    return render_template('index.html', username=session['username'])

@app.route("/ysws-catalog", methods=['GET', 'POST'])
@login_required
def ysws_catalog():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        website = request.form.get('website')
        slack = request.form.get('slack')
        slack_channel = request.form.get('slack_channel')
        status = request.form.get('status')
        deadline = request.form.get('deadline')

        # Switch it to right format your the .yml thingy
        dt = datetime.fromisoformat(deadline)
        dt = dt.replace(second=59)
        deadline = dt.isoformat()

        if all([name, description, website, slack, slack_channel, status, deadline]):
            yml_code = generate_yml(name, description, website, slack, slack_channel, status, dt.isoformat())
            print(yml_code)
            return render_template('ysws_catalog.html', 
                                username=session['username'],
                                yml_code=yml_code,
                                show_result=True)
        else:
            return render_template('ysws_catalog.html', 
                                username=session['username'],
                                error="Please fill in all fields")
    
    return render_template('ysws_catalog.html', username=session['username'])

@app.route("/new", methods=['POST', 'GET'])
def new():
    if request.method == 'POST':
        username = request.form.get('username')
        admin_key = request.form.get('admin_key')
        
        if username and admin_key:
            available_keys = load_json_file(KEYS_FILE)
            
            if admin_key in available_keys:
                available_keys.remove(admin_key)
                save_json_file(KEYS_FILE, available_keys)
                
                users = load_json_file(USERS_FILE)
                user_data = {
                    'username': username,
                    'password': admin_key
                }
                users.append(user_data)
                save_json_file(USERS_FILE, users)
                
                session['username'] = username
                return redirect(url_for('main'))
            else:
                return render_template('new.html', error="Invalid admin key!")
        
    return render_template('new.html')

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Login attempt - Username: {username}, Password: {password}")
        
        if username and password:
            users = load_json_file(USERS_FILE)
            print(f"Loaded users: {users}")
            
            user_exists = any(user['username'] == username and user['password'] == password for user in users)
            print(f"User exists: {user_exists}")
            
            if user_exists:
                session['username'] = username
                print(f"Session set: {session}")
                return redirect(url_for('main'))
            else:
                return render_template('login.html', error="Invalid username or password!")
    
    return render_template('login.html')

@app.route("/debug")
def debug():
    users = load_json_file(USERS_FILE)
    return f"Users: {users}<br>Session: {dict(session)}"

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('new'))

if __name__ == "__main__":
    app.run(debug=True)