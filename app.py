from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
from tools.ysws_catalog import generate_yml
from tools.commits import get_commit_count
from tools.aicheck import get_readme_from_github, detect_ai_probability
from datetime import datetime
import os
import secrets
import json
from tools.chatbot import ask_hackclub_ai
import psutil

app = Flask(__name__)
app.secret_key = '6294d6140ad5b58e8352a1e620d2d845'

# File paths
KEYS_FILE = '/home/jim/admin_keys.json'
USERS_FILE = '/home/jim/users.json'
LOGS_FILE = '/home/jim/activity_logs.json'

def get_ram_usage():
    ram = psutil.virtual_memory()
    used = ram.used / (1024 ** 2)     
    total = ram.total / (1024 ** 2)    
    return f"{used:.0f} MB / {total:.0f} MB"

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000  
        return f"{temp:.1f}°C"
    except FileNotFoundError:
        return "N/A"

@app.route("/stats")
def stats():
    return jsonify({
        "ram": get_ram_usage(),
        "temp": get_cpu_temp()
    })

def log_activity(username, action, details=None):
    logs = load_json_file(LOGS_FILE)
    log_entry = {
        'timestamp': str(datetime.now()),
        'username': username,
        'action': action,
        'details': details
    }
    logs.append(log_entry)

    if len(logs) > 200:
        logs = logs[-200:]

    save_json_file(LOGS_FILE, logs)


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

def load_logs():
    return load_json_file(LOGS_FILE)

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
    
    log_activity(session['username'], 'opened the app')
    return render_template('index.html', username=session['username'])

@app.route("/login", methods=['GET', 'POST'])
def login():

    show_community_modal = "community" in request.args

    if request.method == 'POST':
        admin_key = request.form.get('admin_key', '').strip()
        
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
                log_activity(key_data['name'], 'logged in')
                return redirect(url_for('main'))
            else:
                flash('Invalid admin key', 'error')
    
    return render_template('login.html', show_community_modal=show_community_modal)

@app.route("/team")
@login_required
def team():
    return render_template('team.html')

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
            log_activity(session['username'], 'generated ysws catalog entry', f'name: {name}')
            return render_template('ysws_catalog.html', 
                                username=session['username'],
                                yml_code=yml_code,
                                show_result=True)
        else:
            return render_template('ysws_catalog.html', 
                                username=session['username'],
                                error="Please fill in all fields")
    
    log_activity(session['username'], 'accessed ysws catalog')
    return render_template('ysws_catalog.html', username=session['username'])

@app.route("/github-commits", methods=['GET', 'POST'])
@login_required
def github_commits():
    commit_count = None
    if request.method == 'POST':
        github_url = request.form.get('github_url')
        if github_url:
            commit_count = get_commit_count(github_url)
            log_activity(session['username'], 'searched github commits', f'url: {github_url}')
    
    if request.method == 'GET':
        log_activity(session['username'], 'accessed github commits')
    
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
                    log_activity(session['username'], 'checked readme ai', f'url: {github_url}, score: {percentage}%')
                else:
                    ai_result = {'error': 'Could not fetch README from this repository'}
                    
            except Exception as e:
                ai_result = {'error': f'Error: {str(e)}'}
    
    if request.method == 'GET':
        log_activity(session['username'], 'accessed readme ai check')
    
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
                            log_activity(session['username'], 'checked commits hours ratio', f'slack_id: {slack_id}, project: {project_name}, ratio: {ratio}')
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
    
    if request.method == 'GET':
        log_activity(session['username'], 'accessed commits hours ratio')
    
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
            log_activity(session['username'], 'searched up user on hour finder', f'user_id: {user_id}, project: {projectname or "all"}')
        else:
            hackatime_data = {"error": f"HTTP {response.status_code}"}

    if request.method == 'GET':
        log_activity(session['username'], 'accessed hour finder')

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
            log_activity(session['username'], 'searched up user on fraud checker', f'user_id: {user_id}')
        else:
            hackatime_data = {"error": f"HTTP {response.status_code}"}
    print(trust_value if trust_value is not None else "No trust value found")
    
    if request.method == 'GET':
        log_activity(session['username'], 'accessed fraud checker')
        
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
    
    log_activity(session['username'], 'accessed admin panel')
    
    user_list = []
    for user in users:
        user_list.append({
            'username': user['username'],
            'is_superadmin': user.get('superadmin', False)
        })
    
    user_list.sort(key=lambda x: (not x['is_superadmin'], x['username']))
    
    return render_template('admin.html', username=session['username'], keys=keys, users=user_list, is_superadmin=is_super)

@app.route("/admin/logs")
@login_required
def admin_logs():
    logs = load_logs()
    users = load_users()
    admin_keys = load_admin_keys()
    
    log_activity(session['username'], 'accessed admin logs')
    
    all_users = []
    
    for key_data in admin_keys:
        user_info = {
            'username': key_data['name'],
            'is_superadmin': False
        }
        
        user = next((u for u in users if u['username'] == key_data['name']), None)
        if user and user.get('superadmin', False):
            user_info['is_superadmin'] = True
        
        all_users.append(user_info)
    
    for log in logs:
        user = next((u for u in all_users if u['username'] == log['username']), None)
        log['is_superadmin'] = user.get('is_superadmin', False) if user else False
    
    return render_template('admin_logs.html', username=session['username'], logs=logs, users=all_users)

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
        
        log_activity(session['username'], 'generated admin key', f'for user: {name}')
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
                log_activity(session['username'], 'promoted user to superadmin', f'user: {username}')
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
        log_activity(session['username'], 'revoked admin key', f'key: {key_to_revoke[:8]}...')
        flash('Admin key revoked successfully', 'success')
    
    return redirect(url_for('admin'))

@app.route("/logout")
def logout():
    if 'username' in session:
        log_activity(session['username'], 'logged out')
    session.clear()
    return redirect(url_for('login'))

@app.route("/terminology")
@login_required 
def terminology():
    log_activity(session['username'], 'accessed terminology')
    return render_template('terminology.html', username=session['username'])

@app.route("/airtable-automation-hackatime")
@login_required
def automation_hackatime():
    log_activity(session['username'], 'accessed airtable automation hackatime')
    return render_template('airtable_automation_hackatime_peleg.html', username=session['username'])


@app.route("/chatbot")
@login_required
def chatbot():
    log_activity(session['username'], 'accessed chatbot') #we somehow need to include the prompt in audit logs (FBI)
    return render_template('chatbot.html', username=session['username'])


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_input = request.json.get("message")
    log_activity(session['username'], f'asked chatbot: {user_input}')
    username = session['username']

    ai_response = ask_hackclub_ai(username=username, question=user_input)

    return ai_response

@app.route("/project_summary", methods=['GET', 'POST'])
@login_required
def project_summary():
    try:
        if trust_value is None:
            trust_value = None
    except NameError:
        trust_value = None
    if 'project_summary' not in session:
        session['project_summary'] = None
    project_summary = session['project_summary']
    if 'show_result' not in session:
        session['show_result'] = 1
    if request.method == 'POST':
        if session['show_result'] == 1:
            user_id = request.form.get('id')
            # projectname = request.form.get('projectname')
            projectname = None

            if not user_id:
                return render_template('project_summary.html', 
                                    username=session['username'],
                                    error="Please fill in the user ID")

            url = f"https://hackatime.hackclub.com/api/v1/users/{user_id}/stats?features=projects"
            if projectname:
                url += f"&filter_by_project={projectname}"

            response = requests.get(url)
            if response.status_code == 200:
                project_summary = response.json()
                trust_value_int = project_summary.get('trust_factor', {}).get('trust_value', 0)
                trust_value = True if trust_value_int == 1 else False
                log_activity(session['username'], 'searched up user on hour finder', f'user_id: {user_id}, project: {projectname or "all"}')
            else:
                project_summary = {"error": f"HTTP {response.status_code}"}
            session['show_result'] = 2

            session['project_summary'] = project_summary
            return render_template('project_summary.html', 
                           username=session['username'],
                           summary=project_summary,
                           trust_value=trust_value,
                           show_result=session['show_result'])

        elif session['show_result'] == 2:
            projectname = request.form.get('projectname')
            project_summary = project_summary
            session['show_result'] = 3

            session['project_summary'] = project_summary
            return render_template('project_summary.html', 
                username=session['username'],
                summary=project_summary,
                trust_value=trust_value,
                show_result=session['show_result'])

        print(session['show_result'])

    if request.method == 'GET':
        log_activity(session['username'], 'accessed project summary')

    print(session['show_result'])
    return render_template('project_summary.html', 
                           username=session['username'],
                           summary=project_summary,
                           trust_value=trust_value,
                           show_result=session['show_result'])

@app.route("/dns-github", methods=['GET', 'POST'])
@login_required
def dns_github():
    if request.method == 'POST':
        subdomain_name = request.form.get('name')
        website_link = request.form.get('website')
        ttl = request.form.get('slack')
        
        if not all([subdomain_name, website_link, ttl]):
            return render_template('dns_github.html', 
                                username=session['username'],
                                error="Please fill in all fields")
        
        try:
            # Auto-detect provider based on input format
            if 'github.io' in website_link or 'githubusercontent.com' in website_link:
                # GitHub Pages
                provider = 'github'
                # Clean up the URL - remove https:// if present and ensure proper format
                clean_url = website_link.replace('https://', '').replace('http://', '')
                if not clean_url.endswith('.'):
                    clean_url += '.'
                
                yml_code = f"""# {subdomain_name}.hackclub.com
{subdomain_name}:
  - ttl: {ttl}
    type: CNAME
    value: {clean_url}"""
                log_activity(session['username'], 'generated dns config', f'subdomain: {subdomain_name}.hackclub.com (GitHub Pages)')
                
            elif 'vercel' in website_link or 'vercel-dns.com' in website_link:
                # Vercel - always use cname.vercel-dns.com
                provider = 'vercel'
                
                yml_code = f"""# {subdomain_name}.hackclub.com
{subdomain_name}:
  - ttl: {ttl}
    type: CNAME
    value: cname.vercel-dns.com."""
                log_activity(session['username'], 'generated dns config', f'subdomain: {subdomain_name}.hackclub.com (Vercel)')
                
            else:
                # Default to treating as CNAME
                provider = 'other'
                clean_link = website_link.replace('https://', '').replace('http://', '')
                if not clean_link.endswith('.'):
                    clean_link += '.'
                
                yml_code = f"""# {subdomain_name}.hackclub.com
{subdomain_name}:
  - ttl: {ttl}
    type: CNAME
    value: {clean_link}"""
                log_activity(session['username'], 'generated dns config', f'subdomain: {subdomain_name}.hackclub.com')
            
            return render_template('dns_github.html', 
                                username=session['username'],
                                yml_code=yml_code,
                                show_result=True,
                                subdomain_name=subdomain_name,
                                provider=provider)
        except Exception as e:
            return render_template('dns_github.html', 
                                username=session['username'],
                                error=f"Error generating DNS: {str(e)}")
    
    log_activity(session['username'], 'accessed dns github generator')
    return render_template('dns_github.html', username=session['username'])


@app.route("/faq")
@login_required
def faq():
    log_activity(session['username'], 'accessed faq answer generator')
    return render_template('faq_answer.html')

@app.route("/hcb")
@login_required
def hcb():
    log_activity(session['username'], 'accessed hcb org creator')
    return render_template('hcb.html', username=session['username'])

if __name__ == "__main__":
    if not os.path.exists(KEYS_FILE):
        initial_keys = [
            {
                'name': 'jim',
                'key': 'ill-change-this-ofc',
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
    
    if not os.path.exists(LOGS_FILE):
        initial_logs = []
        save_json_file(LOGS_FILE, initial_logs)
    
    app.run(host='0.0.0.0', port=44195)

