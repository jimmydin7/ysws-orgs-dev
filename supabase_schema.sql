-- Create users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  slack_id TEXT UNIQUE,
  slack_email TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  superadmin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create admin_keys table
CREATE TABLE admin_keys (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  key TEXT UNIQUE NOT NULL,
  generated_by TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create activity_logs table
CREATE TABLE activity_logs (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  username TEXT NOT NULL,
  action TEXT NOT NULL,
  details TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for better performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_admin_keys_key ON admin_keys(key);
CREATE INDEX idx_activity_logs_username ON activity_logs(username);
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp);

-- Add initial superadmin user (same as in the JSON file)
INSERT INTO users (username, superadmin)
VALUES ('admin', TRUE);

-- Add initial admin key (same as in the JSON file)
INSERT INTO admin_keys (name, key, generated_by, generated_at)
VALUES ('admin', '79d47d9bc2c7785396e12f104e3d96bf', 'system', '2024-01-01');


CREATE TABLE invites (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    invited_by TEXT NOT NULL,
    invite_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used_at TIMESTAMPTZ,
    used_by TEXT,
    is_used BOOLEAN DEFAULT FALSE
);

-- Add indexes for better performance
CREATE INDEX idx_invites_email ON invites(email);
CREATE INDEX idx_invites_is_used ON invites(is_used);
CREATE INDEX idx_invites_email_unused ON invites(email, is_used) WHERE is_used = FALSE;