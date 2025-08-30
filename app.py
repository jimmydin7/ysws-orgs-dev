from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from tools.ysws_catalog import generate_yml
from tools.commits import get_commit_count
from tools.aicheck import get_readme_from_github, detect_ai_probability
from datetime import datetime
import os
import secrets
import json

app = Flask(__name__)
app.secret_key = '6294d6140ad5b58e8352a1e620d2d845'

# File paths
KEYS_FILE = 'admin_keys.json'
USERS_FILE = 'users.json'

def load_json_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_json_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_admin_keys():
    return load_json_file(KEYS_FILE)

def load_users():
    return load_json_file(USERS_FILE)

def save_admin_keys(keys):
    save_json_file(KEYS_FILE, keys)

def save_users(users):
    save_json_file(USERS_FILE, users)

def generate_key():
    return secrets.token_hex(16)

def is_superadmin(username):
    users = load_users()
    print(f"Debug: Checking superadmin for username: {username}")
    print(f"Debug: Loaded users: {users}")
    user = next((u for u in users if u['username'] == username), None)
    print(f"Debug: Found user: {user}")
    result = user and user.get('superadmin', False)
    print(f"Debug: Is superadmin: {result}")
    return result

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/")
def main():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html', username=session['username'])

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin_key = request.form.get('admin_key')
        
        if admin_key:
            keys = load_admin_keys()
            print(f"Debug: Admin key entered: {admin_key}")
            print(f"Debug: Available keys: {keys}")
            key_data = next((k for k in keys if k['key'] == admin_key), None)
            print(f"Debug: Found key data: {key_data}")
            
            if key_data:
                session['username'] = key_data['name']
                session['admin_key'] = admin_key
                print(f"Debug: Session username set to: {session['username']}")
                return redirect(url_for('main'))
            else:
                flash('Invalid admin key', 'error')
    
    return render_template('login.html')

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

@app.route("/admin")
@login_required
def admin():
    keys = load_admin_keys()
    users = load_users()
    is_super = is_superadmin(session['username'])
    
    # Create user list with superadmin status and registration dates
    user_list = []
    for user in users:
        # Get registration date from keys if available, otherwise use a default
        key_data = next((k for k in keys if k['name'] == user['username']), None)
        registration_date = key_data['generated_at'] if key_data else 'N/A'
        
        user_list.append({
            'username': user['username'],
            'is_superadmin': user.get('superadmin', False),
            'registration_date': registration_date
        })
    
    # Sort: superadmins first (in red), then normal users
    user_list.sort(key=lambda x: (not x['is_superadmin'], x['username']))
    
    return render_template('admin.html', username=session['username'], keys=keys, users=user_list, is_superadmin=is_super)

@app.route("/admin/generate", methods=['POST'])
@login_required
def generate_admin_key():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('main'))
    
    name = request.form.get('name')
    if name:
        new_key = generate_key()
        keys = load_admin_keys()
        
        key_data = {
            'name': name,
            'key': new_key,
            'generated_by': session['username'],
            'generated_at': str(datetime.now())
        }
        
        keys.append(key_data)
        save_admin_keys(keys)
        
        # Also create a user entry if it doesn't exist
        users = load_users()
        if not any(u['username'] == name for u in users):
            users.append({
                'username': name,
                'superadmin': False
            })
            save_users(users)
        
        flash(f'New admin key generated for {name}: {new_key}', 'success')
    
    return redirect(url_for('admin'))

@app.route("/admin/promote", methods=['POST'])
@login_required
def promote_to_superadmin():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    username = request.form.get('username')
    if username:
        users = load_users()
        for user in users:
            if user['username'] == username:
                user['superadmin'] = True
                save_users(users)
                flash(f'{username} has been promoted to superadmin!', 'success')
                break
        else:
            flash(f'User {username} not found.', 'error')
    
    return redirect(url_for('admin'))

@app.route("/admin/revoke", methods=['POST'])
@login_required
def revoke_admin_key():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('main'))
    
    key_to_revoke = request.form.get('key')
    if key_to_revoke:
        keys = load_admin_keys()
        keys = [k for k in keys if k['key'] != key_to_revoke]
        save_admin_keys(keys)
        flash('Admin key revoked successfully', 'success')
    
    return redirect(url_for('admin'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/terminology")
@login_required 
def terminology():
    return render_template('terminology.html', username=session['username'])

@app.route("/airtable-automation-hackatime")
@login_required
def automation_hackatime():
    return render_template('airtable_automation_hackatime_peleg.html', username=session['username'])

if __name__ == "__main__":
    # Initialize files if they don't exist
    if not os.path.exists(KEYS_FILE):
        initial_keys = [
            {
                'name': 'jim',
                'key': '79d47d9bc2c7785396e12f104e3d96bf',
                'generated_by': 'system',
                'generated_at': '2024-01-01'
            }
        ]
        save_admin_keys(initial_keys)
    
    if not os.path.exists(USERS_FILE):
        initial_users = [
            {
                'username': 'jim',
                'superadmin': True
            }
        ]
        save_users(initial_users)
    
    app.run(debug=True, port=44195)

