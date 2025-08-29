from flask import Flask, render_template, request, redirect, url_for, session
import requests
from config import SECRET_KEY, KEYS_FILE, USERS_FILE
from utils import load_json_file, save_json_file, login_required
from tools.ysws_catalog import generate_yml
from tools.commits import get_commit_count
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

NEST_PORT = 44195

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

@app.route("/github-commits", methods=['GET', 'POST'])
@login_required
def github_commits():
    commit_count = None
    if request.method == 'POST':
        github_url = request.form.get('github_url')
        if github_url:
            commit_count = get_commit_count(github_url)
    
    return render_template('github_commits.html', 
                          username=session['username'],
                          commit_count=commit_count,
                          show_result=commit_count is not None)

@app.route("/hour_finder", methods=['GET', 'POST'])
@login_required
def find_hackatime():
    hackatime_data = None
    trust_value = None
    if request.method == 'POST':
        user_id = request.form.get('id')
        projectname = request.form.get('projectname')

        if not user_id:
            return render_template('hour_finder.html', 
                                   username=session['username'],
                                   error="Please fill in the user ID")

        url = f"https://hackatime.hackclub.com/api/v1/users/{user_id}/stats?features=projects"
        if projectname:
            url += f"&filter_by_project={projectname}"

        response = requests.get(url)
        if response.status_code == 200:
            hackatime_data = response.json()
            trust_value_int = hackatime_data.get('trust_factor', {}).get('trust_value', 0)
            trust_value = True if trust_value_int == 1 else False
        else:
            hackatime_data = {"error": f"HTTP {response.status_code}"}

    return render_template('hour_finder.html', 
                           username=session['username'],
                           hackatime_data=hackatime_data,
                           trust_value=trust_value,
                           show_result=hackatime_data is not None)

@app.route("/fraud_checker", methods=['GET', 'POST'])
@login_required
def fraud_checker():
    hackatime_data = None
    trust_value = None
    if request.method == 'POST':
        user_id = request.form.get('id')

        if not user_id:
            return render_template('fraud_checker.html', 
                                   username=session['username'],
                                   error="Please fill in the user ID")

        url = f"https://hackatime.hackclub.com/api/v1/users/{user_id}/stats"

        response = requests.get(url)
        if response.status_code == 200:
            hackatime_data = response.json()
            trust_value_int = hackatime_data.get('trust_factor', {}).get('trust_value', 0)
            if trust_value_int == 1:
                trust_value = True
            else:
                trust_value = False
            print(trust_value)
            if trust_value_int == None:
                trust_value_int = "Failure To get"
        else:
            hackatime_data = {"error": f"HTTP {response.status_code}"}
    print(trust_value if trust_value is not None else "No trust value found")
    return render_template('fraud_checker.html', 
                           username=session['username'],
                           hackatime_data=hackatime_data,
                           trust_value=trust_value,
                           show_result=hackatime_data is not None)

@app.route("/new", methods=['POST', 'GET'])
def new():
    if request.method == 'POST':
        username = request.form.get('username')
        name = username
        username = username.lower()
        admin_key = request.form.get('admin_key')
        
        if username and admin_key:
            available_keys = load_json_file(KEYS_FILE)
            users = load_json_file(USERS_FILE)

            if username.lower() not in users:
                return render_template('new.html', error="User already exists!")

            if admin_key in available_keys:
                available_keys.remove(admin_key)
                save_json_file(KEYS_FILE, available_keys)
                
                users = load_json_file(USERS_FILE)
                user_data = {
                    'username': username.lower(),
                    'password': admin_key
                }
                users.append(user_data)
                save_json_file(USERS_FILE, users)
                
                session['username'] = name
                return redirect(url_for('main'))
            else:
                return render_template('new.html', error="Invalid admin key!")
        
    return render_template('new.html')

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        name = username
        username = username.lower()
        password = request.form.get('password')
        
        print(f"Login attempt - Username: {name}, Password: {password}")
        
        if username and password:
            users = load_json_file(USERS_FILE)
            print(f"Loaded users: {users}")
            
            user_exists = any(user['username'] == username and user['password'] == password for user in users)
            print(f"User exists: {user_exists}")
            
            if user_exists:
                session['username'] = name
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
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=44195)
