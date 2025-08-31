from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from tools.ysws_catalog import generate_yml
from tools.commits import get_commit_count
from tools.aicheck import get_readme_from_github, detect_ai_probability
from datetime import datetime
import os
import secrets
import json
from dotenv import load_dotenv
from db import (get_users, get_user_by_username, is_superadmin, is_admin, 
               get_admin_keys, get_admin_key, add_admin_key, get_activity_logs, 
               add_activity_log, create_user, update_user, get_user_by_slack_id)
from slack_auth import setup_oauth, handle_slack_callback, get_slack_login_url
import ssl

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', '6294d6140ad5b58e8352a1e620d2d845')
oauth = setup_oauth(app)

def log_activity(username, action, details=None):
    add_activity_log(username, action, details)

def generate_key():
    return secrets.token_hex(16)

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
    if request.method == 'POST':
        admin_key = request.form.get('admin_key')
        
        if admin_key:
            print(f"Debug: Admin key entered: {admin_key}")
            key_data = get_admin_key(admin_key)
            print(f"Debug: Found key data: {key_data}")
            
            if key_data:
                session['username'] = key_data['name']
                session['admin_key'] = admin_key
                print(f"Debug: Session username set to: {session['username']}")
                log_activity(key_data['name'], 'logged in with admin key')
                return redirect(url_for('main'))
            else:
                flash('Invalid admin key', 'error')
    
    return render_template('login.html')

@app.route("/login/slack")
def login_slack():
    """Redirect to Slack OAuth authorization page"""
    return get_slack_login_url(oauth)

@app.route("/slack/callback")
def slack_callback():
    """Handle the callback from Slack OAuth"""
    user_info, error = handle_slack_callback(oauth)
    
    if error:
        flash(error, 'error')
        return redirect(url_for('login'))
    
    user = get_user_by_slack_id(user_info['user_id'])
    
    if not user:
        existing_user = get_user_by_username(user_info['username'])
        
        if existing_user:
            update_user(user_info['username'], {
                'slack_id': user_info['user_id'],
                'slack_email': user_info.get('email')
            })
        else:
            create_user(
                username=user_info['username'],
                slack_id=user_info['user_id'],
                slack_email=user_info.get('email')
            )
    
    return redirect(url_for('main'))

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
    keys = get_admin_keys()
    users = get_users()
    is_super = is_superadmin(session['username'])
    
    # Get invites for superadmins
    invites = []
    if is_super:
        from db import get_all_invites
        invites = get_all_invites()
    
    log_activity(session['username'], 'accessed admin panel')
    
    user_list = []
    for user in users:
        user_list.append({
            'username': user['username'],
            'is_superadmin': user.get('superadmin', False),
            'is_admin': user.get('is_admin', False),
            'slack_email': user.get('slack_email', None)
        })
    
    # Sort by role (superadmin first, then admin, then regular users) and then by username
    user_list.sort(key=lambda x: (not x['is_superadmin'], not x['is_admin'], x['username']))
    
    return render_template('admin.html', 
                          username=session['username'], 
                          keys=keys, 
                          users=user_list, 
                          is_superadmin=is_super,
                          invites=invites)
    
    
@app.route("/admin/invites/create", methods=['POST'])
@login_required
def create_invite_route():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    email = request.form.get('email')
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('admin'))
    
    from db import create_invite
    invite_code = create_invite(email, session['username'])
    
    if invite_code:
        log_activity(session['username'], 'created invite', f'email: {email}')
        flash(f'Invite created for {email}', 'success')
    else:
        flash(f'Invite already exists for {email}', 'error')
    
    return redirect(url_for('admin'))

@app.route("/admin/invites/revoke", methods=['POST'])
@login_required
def revoke_invite_route():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    email = request.form.get('email')
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('admin'))
    
    from db import revoke_invite
    success = revoke_invite(email)
    
    if success:
        log_activity(session['username'], 'revoked invite', f'email: {email}')
        flash(f'Invite revoked for {email}', 'success')
    else:
        flash(f'No pending invite found for {email}', 'error')
    
    return redirect(url_for('admin'))


@app.route("/admin/logs")
@login_required
def admin_logs():
    logs = get_activity_logs()
    users = get_users()
    admin_keys = get_admin_keys()
    
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
        generated_at = str(datetime.now())
        
        add_admin_key(name, new_key, session['username'], generated_at)
        
        log_activity(session['username'], 'generated admin key', f'for user: {name}')
        flash(f'New admin key generated for {name}: {new_key}', 'success')
    
    return redirect(url_for('admin'))

@app.route("/admin/promote", methods=['POST'])
@login_required
def promote_user():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    username = request.form.get('username')
    role = request.form.get('role', 'admin')
    
    if username:
        try:
            if role == 'superadmin':
                from db import promote_to_superadmin
                promote_to_superadmin(username)
                log_activity(session['username'], 'promoted user to superadmin', f'user: {username}')
                flash(f'{username} has been promoted to superadmin!', 'success')
            else:
                from db import promote_to_admin
                promote_to_admin(username)
                log_activity(session['username'], 'promoted user to admin', f'user: {username}')
                flash(f'{username} has been promoted to admin!', 'success')
        except Exception as e:
            flash(f'Error promoting user: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route("/admin/demote", methods=['POST'])
@login_required
def demote_user():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    username = request.form.get('username')
    if username:
        try:
            from db import demote_user as demote
            demote(username)
            log_activity(session['username'], 'demoted user', f'user: {username}')
            flash(f'{username} has been demoted to regular user!', 'success')
        except Exception as e:
            flash(f'Error demoting user: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route("/admin/revoke", methods=['POST'])
@login_required
def revoke_admin_key():
    if not is_superadmin(session['username']):
        flash('Access denied. Superadmin privileges required.', 'error')
        return redirect(url_for('admin'))
    
    key_to_revoke = request.form.get('key')
    if key_to_revoke:
        try:
            from db import revoke_admin_key
            revoke_admin_key(key_to_revoke)
            log_activity(session['username'], 'revoked admin key', f'key: {key_to_revoke[:8]}...')
            flash('Admin key revoked successfully', 'success')
        except Exception as e:
            flash(f'Error revoking key: {str(e)}', 'error')
    
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
    log_activity(session['username'], 'accessed chatbot')
    return render_template('chatbot.html', username=session['username'])


@app.route("/dns-github", methods=['GET', 'POST'])
@login_required
def dns_github():
    if request.method == 'POST':
        subdomain_name = request.form.get('name')
        github_pages_url = request.form.get('website')
        ttl = request.form.get('slack')
        
        if all([subdomain_name, github_pages_url, ttl]):
            try:
                yml_code = f"""# {subdomain_name}.hackclub.com
{subdomain_name}:
  - type: CNAME
    value: {github_pages_url}.
    ttl: {ttl}"""
                
                log_activity(session['username'], 'generated dns config', f'subdomain: {subdomain_name}.hackclub.com')
                return render_template('dns_github.html', 
                                    username=session['username'],
                                    yml_code=yml_code,
                                    show_result=True,subdomain_name=subdomain_name)
            except Exception as e:
                return render_template('dns_github.html', 
                                    username=session['username'],
                                    error=f"Error generating DNS: {str(e)}")
        else:
            return render_template('dns_github.html', 
                                username=session['username'],
                                error="Please fill in all fields")
    
    log_activity(session['username'], 'accessed dns github generator')
    return render_template('dns_github.html', username=session['username'])

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run the Grounded Tracker application')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
    port = args.port
    
    print("\n" + "=" * 50)
    print("HTTPS CONFIGURATION")
    print("=" * 50)
    
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        cert_file = 'cert.pem'
        key_file = 'key.pem'
        
        if os.path.exists(cert_file) and os.path.exists(key_file):
            context.load_cert_chain(cert_file, key_file)
            print("✓ SSL certificates found")
            print(f"🚀 Starting HTTPS server at https://127.0.0.1:{port}")
            app.run(debug=True, port=port, ssl_context=context)
        else:
            print("⚠️  SSL certificates not found!")
            print("To generate self-signed certificates, run:")
            print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")
            print("\nAlternatively, running on HTTP for now...")
            print(f"🚀 Starting HTTP server at https://localhost:{port}")
            app.run(debug=True, port=port)
            
    except Exception as e:
        print(f"❌ SSL setup failed: {e}")
        print(f"🚀 Starting HTTP server at https://localhost:{port}")
        app.run(debug=True, port=port)
        
        