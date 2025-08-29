from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from config import SECRET_KEY, KEYS_FILE, USERS_FILE
from utils import load_json_file, save_json_file, login_required
from tools.ysws_catalog import generate_yml
from tools.commits import get_commit_count
from tools.aicheck import get_readme_from_github, detect_ai_probability
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

NEST_PORT = 44195

@app.route("/", methods=['GET', 'POST'])
@login_required
def main():
    print(session['is_admin'])
    error = None
    return render_template('index.html', username=session['username'], is_admin=session.get('is_admin', False), error=error)

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

@app.route("/readme-ai-check", methods=['GET', 'POST'])
@login_required
def readme_ai_check():
    ai_result = None
    if request.method == 'POST':
        github_url = request.form.get('github_url')
        if github_url:
            try:
                readme_content = get_readme_from_github(github_url)
                
                if readme_content:
                    ai_probability = detect_ai_probability(readme_content)
                    
                    try:
                        if '<think>' in ai_probability and '</think>' in ai_probability:
                            parts = ai_probability.split('</think>')
                            if len(parts) > 1:
                                probability_str = parts[1].strip()
                                probability_float = float(probability_str)
                            else:
                                probability_float = 0.0
                        else:
                            probability_float = float(ai_probability)
                        
                        percentage = int(probability_float * 100)
                    except:
                        percentage = 0
                    
                    ai_result = {
                        'score': percentage,
                        'probability': ai_probability,
                        'content': readme_content[:300] + "..." if len(readme_content) > 300 else readme_content
                    }
                else:
                    ai_result = {'error': 'Could not fetch README from this repository'}
                    
            except Exception as e:
                ai_result = {'error': f'Error: {str(e)}'}
    
    return render_template('readme_ai_check.html', 
                          username=session['username'],
                          ai_result=ai_result,
                          show_result=ai_result is not None)

@app.route("/commits-hours-ratio", methods=['GET', 'POST'])
@login_required
def commits_hours_ratio():
    ratio_data = None
    if request.method == 'POST':
        slack_id = request.form.get('slack_id')
        project_name = request.form.get('project_name')
        github_url = request.form.get('github_url')
        
        if all([slack_id, project_name, github_url]):
            try:
                url = f"https://hackatime.hackclub.com/api/v1/users/{slack_id}/stats?features=projects"
                response = requests.get(url)
                
                if response.status_code == 200:
                    hackatime_data = response.json()
                    print(f"HackaTime API response: {hackatime_data}")
                    
                    projects_array = hackatime_data.get('data', {}).get('projects', [])
                    print(f"Projects array: {projects_array}")
                    
                    project_found = None
                    for project in projects_array:
                        if project.get('name') == project_name:
                            project_found = project
                            break
                    
                    if project_found:
                        print(f"Project found: {project_found}")
                        hours = project_found.get('total_seconds', 0) / 3600
                        
                        commit_count = get_commit_count(github_url)
                        print(f"Commit count: {commit_count}")
                        
                        if isinstance(commit_count, int) and hours > 0:
                            ratio = commit_count / hours
                            ratio_data = {
                                'commits': commit_count,
                                'hours': round(hours, 2),
                                'ratio': round(ratio, 2)
                            }
                        else:
                            ratio_data = {'error': f'Invalid commit count ({commit_count}) or zero hours ({hours})'}
                    else:
                        available_projects = [p.get('name') for p in projects_array]
                        ratio_data = {'error': f'Project "{project_name}" not found. Available projects: {available_projects}'}
                else:
                    ratio_data = {'error': f'HackaTime API error: {response.status_code} - {response.text}'}
                    
            except Exception as e:
                ratio_data = {'error': f'Error: {str(e)}'}
                print(f"Exception in commits_hours_ratio: {e}")
        else:
            ratio_data = {'error': 'Please fill in all fields'}
    
    return render_template('commits_hours_ratio.html', 
                          username=session['username'],
                          ratio_data=ratio_data,
                          show_result=ratio_data is not None)

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

            if any(u["username"] == username for u in users):
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
        raw_name = username
        username = username.lower()
        password = request.form.get('password')
        
        print(f"Login attempt - Username: {raw_name}, Password: {password}")
        
        if username and password:
            users = load_json_file(USERS_FILE)
            print(f"Loaded users: {users}")
            
            user = next((u for u in users if u['username'] == username and u['password'] == password), None)
            
            if user:
                session['username'] = raw_name
                session['is_admin'] = user.get('admin', False)
                session['is_superuser'] = user.get('superuser', False)
                print(f"Session set: {session}")
                return redirect(url_for('main'))
            else:
                return render_template('login.html', error="Invalid username or password!")
    
    return render_template('login.html')

@app.route("/admin", methods=['POST', 'GET'])
@login_required
def admin():
    name = session['username']
    users = load_json_file(USERS_FILE)
    is_admin = session.get('is_admin', False)


    if not is_admin:
        flash("You must be an admin to access this page!", "error")
        return redirect(url_for('main'))

# POST

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')

        if action == "remove":
            users = load_json_file(USERS_FILE)
            new_users = [u for u in users if u["username"] != username]
            if len(new_users) < len(users):
                save_json_file(USERS_FILE, new_users)
                flash(f"User {username} removed.", "success")
            else:
                flash(f"User {username} not found!", "error")
            return redirect(url_for('admin'))

        if action == "update":
            username = request.form.get('username')

            password = request.form.get('password')
            is_admin = True if request.form.get('is_admin') == "true" else False
            for user in users:
                if user["username"] == username:
                    user["password"] = password
                    user["admin"] = is_admin
                    user["superuser"] = user.get("superuser", False)
                    break
            save_json_file(USERS_FILE, users)
        
        return redirect(url_for('admin'))

#GET

    is_superuser = session.get('is_superuser', False)
    return render_template('admin.html',
                           username=name,
                           users=users,
                           is_admin=is_admin,
                           is_superuser=is_superuser)


@app.route("/admin/remove", methods=["POST"])
@login_required
def remove_user():
    print("Running remove_user")
    users = load_json_file(USERS_FILE)
    username = request.form.get("username")

    new_users = [user for user in users if user["username"] != username]

    if len(new_users) < len(users):
        save_json_file(USERS_FILE, new_users)
        flash(f"User {username} removed.", "success")
    else:
        flash(f"User {username} not found!", "error")

    return redirect(url_for("admin"))

@app.route("/debug")
def debug():
    users = load_json_file(USERS_FILE)
    return f"Users: {users}<br>Session: {dict(session)}"

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))



@app.route("/airtable-automation-hackatime")
@login_required
def automation_hackatime():
    return render_template('airtable_automation_hackatime_peleg.html', username=session['username'])
if __name__ == "__main__":
    
    app.run(debug=True, port=44195)
