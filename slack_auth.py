import os
import requests
import urllib.parse
from flask import redirect, url_for, session, request
from dotenv import load_dotenv
from db import get_user_by_username, get_users, add_activity_log

load_dotenv()

# Get allowed workspaces from environment
ALLOWED_WORKSPACES = os.getenv('ALLOWED_SLACK_WORKSPACES', '').split(',')

def setup_oauth(app):
    """Setup OAuth for the Flask app - not needed for manual implementation"""
    return None

def is_valid_slack_workspace(team_id):
    """Check if the Slack workspace is allowed"""
    return team_id in ALLOWED_WORKSPACES

def get_slack_user_info(access_token):
    """Get user information from Slack using OAuth v2 identity endpoint"""
    try:
        # Use the identity endpoint for OAuth v2
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.get('https://slack.com/api/users.identity', headers=headers)
        data = response.json()
        
        if data.get('ok'):
            user_data = data['user']
            team_data = data['team']
            
            return {
                'user_id': user_data['id'],
                'team_id': team_data['id'],
                'username': user_data['name'],
                'real_name': user_data.get('real_name', user_data['name']),
                'email': user_data.get('email'),
                'team_name': team_data['name']
            }
        else:
            print(f"Slack API error: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error getting Slack user info: {e}")
    
    return None

def exchange_code_for_token(code, redirect_uri):
    """Exchange authorization code for access token"""
    try:
        data = {
            'client_id': os.getenv('SLACK_CLIENT_ID'),
            'client_secret': os.getenv('SLACK_CLIENT_SECRET'),
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = requests.post('https://slack.com/api/oauth.v2.access', data=data)
        token_data = response.json()
        
        if token_data.get('ok'):
            return token_data.get('authed_user', {}).get('access_token')
        else:
            print(f"Token exchange error: {token_data.get('error')}")
            return None
            
    except Exception as e:
        print(f"Error exchanging code for token: {e}")
        return None

def handle_slack_callback(oauth_instance=None):
    """Handle the Slack OAuth callback - manual implementation"""
    try:
        # Get authorization code and state from callback
        code = request.args.get('code')
        error = request.args.get('error')
        returned_state = request.args.get('state')
        
        if error:
            return None, f"OAuth error: {error}"
        
        if not code:
            return None, "No authorization code received"
        
        # Verify CSRF state
        stored_state = session.get('oauth_state')
        if not stored_state or stored_state != returned_state:
            return None, "CSRF state verification failed"
        
        # Clear the state from session after verification
        session.pop('oauth_state', None)
        
        # Exchange code for token
        redirect_uri = url_for('slack_callback', _external=True)
        access_token = exchange_code_for_token(code, redirect_uri)
        
        if not access_token:
            return None, "Could not get access token from Slack"
        
        # Get user info from Slack
        user_info = get_slack_user_info(access_token)
        
        if not user_info:
            return None, "Could not get user info from Slack"
        
        # Check if user's workspace is allowed (skip if no workspaces specified)
        if ALLOWED_WORKSPACES and ALLOWED_WORKSPACES != ['']:
            if not is_valid_slack_workspace(user_info['team_id']):
                return None, f"Your Slack workspace '{user_info['team_name']}' is not authorized to use this application"
        
        # Check if user exists in our database
        existing_user = get_user_by_username(user_info['username'])
        
        # If user doesn't exist, check for invite
        if not existing_user:
            user_email = user_info.get('email')
            if not user_email:
                return None, "Unable to get your email from Slack. Email is required for registration."
            
            # Check if there's a pending invite for this email
            from db import get_pending_invite, consume_invite
            invite = get_pending_invite(user_email)
            
            if not invite:
                return None, f"scram lil vro, dm @Aarav J if ur desperate but I wouldnt count on it"
            
            # Create new user account
            from db import create_user
            create_user(
                username=user_info['username'],
                slack_id=user_info['user_id'],
                slack_email=user_email
            )
            
            # Mark invite as used
            consume_invite(user_email, user_info['username'])
            
            add_activity_log(user_info['username'], 'registered via Slack invite', f'email: {user_email}')
            
        else:
            # Existing user - just update Slack info if needed
            if not existing_user.get('slack_id'):
                from db import update_user
                update_user(user_info['username'], {
                    'slack_id': user_info['user_id'],
                    'slack_email': user_info.get('email')
                })
        
        # Store relevant info in session
        session['slack_token'] = access_token
        session['username'] = user_info['username']
        session['slack_user_id'] = user_info['user_id']
        session['slack_team_id'] = user_info['team_id']
        session['slack_email'] = user_info.get('email')
        
        # Log the activity
        add_activity_log(user_info['username'], 'logged in via Slack')
        
        return user_info, None
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return None, f"OAuth callback error: {str(e)}"

def get_slack_login_url(oauth_instance=None):
    """Get the Slack login URL - completely manual"""
    import secrets
    
    # Generate and store CSRF state
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Manual OAuth v2 URL construction
    client_id = os.getenv('SLACK_CLIENT_ID')
    redirect_uri = url_for('slack_callback', _external=True)
    
    # Build OAuth v2 URL manually
    params = {
        'client_id': client_id,
        'user_scope': 'identity.basic,identity.email,identity.team',
        'redirect_uri': redirect_uri,
        'state': state
    }
    
    oauth_url = 'https://slack.com/oauth/v2/authorize?' + urllib.parse.urlencode(params)
    
    print(f"Generated OAuth v2 URL: {oauth_url}")  # Debug line
    
    return redirect(oauth_url)