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

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
SLACK_CLIENT_ID = "2210535565.9420943297447"
SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')
SLACK_REDIRECT_URI = "https://ysws.jimdinias.dev/auth/slack/callback"

def load_authorized_users():
    try:
        with open('slack_users.json', 'r') as f:
            data = json.load(f)
            return data.get('authorized_users', {})
    except FileNotFoundError:
        return {}

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('slack_auth'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/")
def main():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html', username=session['username'])

@app.route("/login")
def login():
    if 'username' in session:
        return redirect(url_for('main'))
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

        url = f"https://hackatime.hackclub.com/api/v1/users/stats"

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
    authorized_users = load_authorized_users()
    return render_template('admin.html', 
                          username=session['username'],
                          authorized_users=authorized_users)

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

@app.route('/auth/slack')
def slack_auth():
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    slack_auth_url = (
        f"https://slack.com/openid/connect/authorize"
        f"?response_type=code"
        f"&scope=openid%20profile%20email"
        f"&client_id={SLACK_CLIENT_ID}"
        f"&redirect_uri={SLACK_REDIRECT_URI}"
        f"&state={state}"
    )
    return redirect(slack_auth_url)

@app.route('/auth/slack/callback')
def slack_callback():
    if request.args.get('state') != session.get('oauth_state'):
        return "Invalid state parameter", 400
    
    code = request.args.get('code')
    if not code:
        return "No authorization code received", 400
    
    token_response = requests.post('https://slack.com/api/openid.connect.token', data={
        'client_id': SLACK_CLIENT_ID,
        'client_secret': SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': SLACK_REDIRECT_URI
    })
    
    token_data = token_response.json()
    if not token_data.get('ok'):
        return "Failed to get access token", 400
    
    access_token = token_data['access_token']
    
    user_response = requests.get('https://slack.com/api/openid.connect.userInfo', 
                                headers={'Authorization': f'Bearer {access_token}'})
    user_data = user_response.json()
    
    if user_data.get('ok'):
        slack_user_id = user_data['sub']
        authorized_users = load_authorized_users()
        
        if slack_user_id not in authorized_users:
            return "Access denied. You are not authorized to use this application.", 403
        
        user_info = authorized_users[slack_user_id]
        
        session['username'] = user_info['username']
        session['slack_user_id'] = slack_user_id
        
        session.pop('oauth_state', None)
        
        return redirect(url_for('main'))
    
    return "Failed to get user info", 400

if __name__ == "__main__":
    app.run(debug=True, port=44195)

