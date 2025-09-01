# YSWS Organizer Panel

YSWS Organizer Panel is a Flask web application that provides various tools for managing YSWS (You Ship, We Sponsor) operations. The application includes tools for GitHub analysis, fraud checking, AI detection, project tracking, and administrative functions.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

- Bootstrap and run the repository:
  - `python -m venv venv` -- takes ~3 seconds
  - `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows) 
  - `pip install -r requirements.txt` -- **FAILS due to network timeouts**
  - **CRITICAL ISSUE**: `pip install` consistently fails with "ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443): Read timed out." in this environment
  - **WORKAROUND**: Use system Python with globally installed packages if available, or manually copy dependencies from a working environment
  - `python app.py` -- starts Flask development server on port 44195

- Validate Python syntax:
  - `python -m py_compile app.py tools/*.py` -- takes <1 second

- **CRITICAL**: The app runs on port 44195, NOT port 5000 as mentioned in README.md
- **CRITICAL**: Authentication is required - DO NOT modify the auth system (admin_keys.json, users.json). Use the dev key `79d47d9bc2c7785396e12f104e3d96bf` for testing.

## Authentication & Testing

- Test user credentials:
  - Admin key: `79d47d9bc2c7785396e12f104e3d96bf`
  - Username: `dev` (automatically created)
- Access URLs:
  - App: http://localhost:44195 (redirects to login if not authenticated)
  - After login: Main dashboard with tool cards
- Test login process: Enter admin key → Click "Login" → Access main dashboard

## Validation

- Always test authentication by logging in with the dev key before making changes
- **MANDATORY VALIDATION SCENARIO**: After any code changes, run through this complete end-to-end test:
  1. Start the application: `python app.py`
  2. Navigate to http://localhost:44195
  3. Log in with admin key: `79d47d9bc2c7785396e12f104e3d96bf`
  4. Test at least one tool (e.g., click "Terminology" to verify navigation works)
  5. Verify the tool loads correctly and displays expected content
- Always validate Python syntax with `python -m py_compile` before committing
- The application has no formal test suite - manual functional testing is required

## Build Times & Timeouts

- Virtual environment creation: ~3 seconds
- Dependency installation: **FAILS due to network limitations** 
- Application startup: <2 seconds (when dependencies available)
- Python syntax check: <1 second
- **CRITICAL**: Dependency installation consistently fails in restricted network environments
- **NOTE**: No long-running builds in this project when setup works - all operations complete quickly

## Common Tasks

The following are outputs from frequently run commands. Reference them instead of running bash commands to save time.

### Repository Structure
```
.
├── README.md
├── requirements.txt
├── app.py                 # Main Flask application
├── admin_keys.json        # Admin authentication keys
├── users.json            # User accounts
├── activity_logs.json    # Application activity logs
├── tools/                # Tool modules
│   ├── aicheck.py        # README AI detection
│   ├── chatbot.py        # YSWS AI chatbot
│   ├── commits.py        # GitHub commit counter
│   └── ysws_catalog.py   # YSWS catalog generator
├── templates/            # HTML templates
├── static/              # CSS/JS assets
└── venv/               # Virtual environment (created during setup)
```

### Requirements (requirements.txt)
```
Flask==3.0.0
Werkzeug==3.0.1
Jinja2==3.1.2
MarkupSafe==2.1.3
itsdangerous==2.1.2
click==8.1.7
blinker==1.7.0
requests
python-dotenv
```

### Main Application Routes
Key routes in app.py:
- `/` - Main dashboard (requires authentication)
- `/login` - Authentication page
- `/admin` - Admin panel (superadmin only) 
- `/github-commits` - GitHub commit counter tool
- `/readme-ai-check` - AI detection for README files
- `/commits-hours-ratio` - Commits vs HackaTime hours analysis
- `/fraud_checker` - User trust level verification
- `/terminology` - YSWS terminology dictionary
- `/chatbot` - YSWS AI assistant
- `/dns-github` - DNS configuration generator

### Available Tools
1. **GitHub Commit Counter**: Counts total commits in any GitHub repository
2. **README AI Check**: Analyzes README files for AI-generated content  
3. **Commits/Hours Ratio**: Compares GitHub commits to HackaTime hours
4. **Project Hour Finder**: Tracks HackaTime project hours
5. **Fraud Checker**: Checks user trust levels and ban status
6. **Airtable Hours Automation**: Automates hour tracking in Airtable
7. **Terminology**: YSWS-related definitions and terms
8. **DNS Generator**: Creates DNS configs for GitHub Pages
9. **AI Chatbot**: YSWS-focused AI assistant
10. **Catalog Entry Tool**: Generates YML for YSWS catalog
11. **Admin Panel**: User and key management (superadmin only)

### Important Files to Check After Changes
- Always verify `app.py` for route definitions and authentication
- Check `tools/` directory when modifying tool functionality  
- Review `templates/` for HTML template changes
- Examine `admin_keys.json` and `users.json` only for debugging auth issues (DO NOT MODIFY)

## Critical Warnings

- **NEVER** modify authentication system (admin_keys.json, users.json, auth routes)
- **NEVER** commit sensitive data or API keys
- **CRITICAL LIMITATION**: Package installation via pip fails in this environment due to network restrictions
- **ALWAYS** test authentication flow after any changes (when dependencies are available)
- **ALWAYS** verify the app starts on port 44195, not 5000
- The GitHub API tools may receive 403 errors due to rate limiting - this is expected behavior
- Some tools require external APIs (HackaTime, GitHub) which may be unavailable during testing
- In environments with network restrictions, manual dependency management may be required

## Key Development Notes

- Flask app runs in debug mode by default
- Session management uses Flask sessions with secret key
- Activity logging is built-in for user actions
- Tools are modular - each tool has its own Python module in `tools/` directory
- No formal testing framework - rely on manual functional testing
- Authentication is key-based, not username/password
- Admin panel allows key generation and user promotion (superadmin only)