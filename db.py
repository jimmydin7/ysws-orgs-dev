import os
from supabase import create_client
from dotenv import load_dotenv
import secrets
from datetime import datetime


load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def get_users():
    response = supabase.table('users').select('*').execute()
    return response.data

def get_user_by_username(username):
    response = supabase.table('users').select('*').eq('username', username).execute()
    return response.data[0] if response.data else None

def get_user_by_slack_id(slack_id):
    response = supabase.table('users').select('*').eq('slack_id', slack_id).execute()
    return response.data[0] if response.data else None

def create_user(username, slack_id=None, slack_email=None, is_admin=False, is_superadmin=False):
    data = {
        'username': username,
        'slack_id': slack_id,
        'slack_email': slack_email,
        'is_admin': is_admin,
        'superadmin': is_superadmin
    }
    response = supabase.table('users').insert(data).execute()
    return response.data[0] if response.data else None

def update_user(username, data):
    response = supabase.table('users').update(data).eq('username', username).execute()
    return response.data[0] if response.data else None

def is_superadmin(username):
    user = get_user_by_username(username)
    return user and user.get('superadmin', False)

def is_admin(username):
    user = get_user_by_username(username)
    return user and (user.get('is_admin', False) or user.get('superadmin', False))

def get_admin_keys():
    response = supabase.table('admin_keys').select('*').execute()
    return response.data

def get_admin_key(key):
    response = supabase.table('admin_keys').select('*').eq('key', key).execute()
    return response.data[0] if response.data else None

def add_admin_key(name, key, generated_by, generated_at):
    data = {
        'name': name,
        'key': key,
        'generated_by': generated_by,
        'generated_at': generated_at
    }
    response = supabase.table('admin_keys').insert(data).execute()
    return response.data

def revoke_admin_key(key):
    response = supabase.table('admin_keys').delete().eq('key', key).execute()
    return response.data

def promote_to_superadmin(username):
    response = supabase.table('users').update({'superadmin': True, 'is_admin': True}).eq('username', username).execute()
    return response.data

def promote_to_admin(username):
    response = supabase.table('users').update({'is_admin': True, 'superadmin': False}).eq('username', username).execute()
    return response.data

def demote_user(username):
    response = supabase.table('users').update({'is_admin': False, 'superadmin': False}).eq('username', username).execute()
    return response.data

def get_activity_logs():
    response = supabase.table('activity_logs').select('*').order('timestamp', desc=True).execute()
    return response.data

def add_activity_log(username, action, details=None):
    data = {
        'username': username,
        'action': action,
        'details': details,
        'timestamp': 'now()'
    }
    response = supabase.table('activity_logs').insert(data).execute()
    return response.data

def create_invite(email, invited_by):
    """Create a new invite for an email"""
    invite_code = secrets.token_urlsafe(32)
    created_at = datetime.now().isoformat()
    
    try:
        data = {
            'email': email,
            'invited_by': invited_by,
            'invite_code': invite_code,
            'created_at': created_at,
            'is_used': False
        }
        response = supabase.table('invites').insert(data).execute()
        return invite_code
    except Exception as e:
        print(f"Error creating invite: {e}")
        # Check if email already has an invite
        existing = get_pending_invite(email)
        if existing:
            return None
        return None

def get_pending_invite(email):
    """Get a pending (unused) invite for an email"""
    try:
        response = supabase.table('invites').select('*').eq('email', email).eq('is_used', False).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting pending invite: {e}")
        return None

def consume_invite(email, used_by):
    """Mark an invite as used"""
    used_at = datetime.now().isoformat()
    
    try:
        response = supabase.table('invites').update({
            'is_used': True,
            'used_at': used_at,
            'used_by': used_by
        }).eq('email', email).eq('is_used', False).execute()
        return response.data
    except Exception as e:
        print(f"Error consuming invite: {e}")
        return None

def get_all_invites():
    """Get all invites for admin view"""
    try:
        response = supabase.table('invites').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error getting all invites: {e}")
        return []

def revoke_invite(email):
    """Revoke (delete) an unused invite"""
    try:
        response = supabase.table('invites').delete().eq('email', email).eq('is_used', False).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error revoking invite: {e}")
        return False