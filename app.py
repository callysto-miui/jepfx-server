from flask import Flask, request, jsonify, render_template_string, Response
import hashlib
from datetime import datetime, timedelta
import uuid
import json
import os
import threading
import time
import secrets

app = Flask(__name__)

# ==================================================
# 📂 PERMANENT DATA SAVE
# ==================================================
DATA_FILE = "server_data.json"

# ==================================================
# 🎨 THEME SETTINGS
# ==================================================
THEMES = {
    "dark": {
        "bg_gradient": "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
        "primary": "#7C3AED",
        "secondary": "#10B981",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#AAAAAA",
        "card_bg": "rgba(255,255,255,0.1)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(255,255,255,0.2)"
    },
    "light": {
        "bg_gradient": "linear-gradient(135deg, #f5f7fa, #c3cfe2)",
        "primary": "#6D28D9",
        "secondary": "#059669",
        "danger": "#DC2626",
        "warning": "#D97706",
        "text": "#1F2937",
        "text_secondary": "#6B7280",
        "card_bg": "rgba(255,255,255,0.9)",
        "input_bg": "rgba(255,255,255,0.8)",
        "border": "rgba(0,0,0,0.1)"
    },
    "blue": {
        "bg_gradient": "linear-gradient(135deg, #1e3c72, #2a5298)",
        "primary": "#3B82F6",
        "secondary": "#22C55E",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#CBD5E1",
        "card_bg": "rgba(59,130,246,0.2)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(59,130,246,0.3)"
    },
    "green": {
        "bg_gradient": "linear-gradient(135deg, #0f2027, #203a43, #2c5364)",
        "primary": "#10B981",
        "secondary": "#34D399",
        "danger": "#EF4444",
        "warning": "#F59E0B",
        "text": "#FFFFFF",
        "text_secondary": "#A7F3D0",
        "card_bg": "rgba(16,185,129,0.15)",
        "input_bg": "rgba(0,0,0,0.3)",
        "border": "rgba(16,185,129,0.3)"
    },
    "midnight": {
        "bg_gradient": "linear-gradient(135deg, #000428, #004e92)",
        "primary": "#8B5CF6",
        "secondary": "#A78BFA",
        "danger": "#F87171",
        "warning": "#FBBF24",
        "text": "#FFFFFF",
        "text_secondary": "#C4B5FD",
        "card_bg": "rgba(139,92,246,0.15)",
        "input_bg": "rgba(0,0,0,0.4)",
        "border": "rgba(139,92,246,0.3)"
    }
}

CURRENT_THEME = "dark"

def get_theme_css():
    theme = THEMES.get(CURRENT_THEME, THEMES["dark"])
    return f"""
    :root {{
        --bg-gradient: {theme["bg_gradient"]};
        --primary: {theme["primary"]};
        --secondary: {theme["secondary"]};
        --danger: {theme["danger"]};
        --warning: {theme["warning"]};
        --text: {theme["text"]};
        --text-secondary: {theme["text_secondary"]};
        --card-bg: {theme["card_bg"]};
        --input-bg: {theme["input_bg"]};
        --border: {theme["border"]};
    }}
    body {{ background: var(--bg-gradient); color: var(--text); min-height: 100vh; padding: 20px; transition: all 0.3s ease; }}
    .card, .stat-card, .result-box, .modal-content, .login-box {{ background: var(--card-bg); backdrop-filter: blur(10px); }}
    input, select, textarea {{ background: var(--input-bg); color: var(--text); border-color: var(--border); }}
    button {{ background: var(--primary); }}
    button:hover {{ filter: brightness(1.1); transform: translateY(-2px); }}
    .tab {{ background: rgba(255,255,255,0.1); color: var(--text); }}
    .tab.active {{ background: var(--primary); }}
    .stat-card:hover {{ transform: translateY(-5px); transition: 0.3s; cursor: pointer; }}
    th {{ background: {theme["primary"]}40; }}
    tr:hover {{ background: rgba(255,255,255,0.05); }}
    .pre-style {{ font-family: monospace; white-space: pre; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; overflow-x: auto; font-size: 13px; line-height: 1.6; }}
    .copy-btn {{ background: var(--primary); padding: 2px 8px; border-radius: 5px; font-size: 11px; margin-left: 5px; cursor: pointer; display: inline-block; }}
    .btn-danger {{ background: var(--danger); }}
    .btn-success {{ background: var(--secondary); }}
    .btn-warning {{ background: var(--warning); }}
    .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }}
    .modal-content {{ margin: 5% auto; padding: 25px; border-radius: 15px; width: 90%; max-width: 500px; position: relative; }}
    .close {{ float: right; font-size: 28px; cursor: pointer; }}
    .tabs {{ display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 20px; }}
    .content {{ display: none; border-radius: 15px; padding: 25px; }}
    .content.active {{ display: block; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
    .stat-number {{ font-size: 28px; font-weight: bold; color: var(--primary); }}
    """
    
THEME_SELECTOR_HTML = """
<div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
    <select id="themeSelect" onchange="changeTheme(this.value)" style="padding: 8px 15px; border-radius: 20px; background: var(--card-bg); color: var(--text); border: 1px solid var(--border); cursor: pointer;">
        <option value="dark" style="background:#0f0c29">🌙 Dark</option>
        <option value="light" style="background:#f5f7fa; color:#000">☀️ Light</option>
        <option value="blue" style="background:#1e3c72">🔵 Blue</option>
        <option value="green" style="background:#0f2027">🌿 Green</option>
        <option value="midnight" style="background:#000428">🌌 Midnight</option>
    </select>
</div>
<script>
function changeTheme(theme) {
    fetch('/api/set-theme', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({theme: theme})
    }).then(() => location.reload());
}
</script>
"""

# ==================================================
# 🔐 ADMIN SETTINGS
# ==================================================
MASTER_ADMIN = {
    "username": "JEPFX",
    "password": "JEPFXADMIN",
    "role": "master",
    "credits": 999999,
    "created_at": None
}

ADMINS = {}
MODERATORS = {}

# ==================================================
# 📝 LICENSES & USERS
# ==================================================
PERMANENT_LICENSES = {}
CUSTOM_ACTIVATIONS = {}
TRIAL_LICENSES = {}
TRIAL_USERS = {}
USAGE_LOGS = {}

# ==================================================
# 📜 LICENSE HISTORY
# ==================================================
LICENSE_HISTORY = []

# ==================================================
# 📨 USER REQUESTS
# ==================================================
USER_REQUESTS = []

VALID_USERS = {
    "JEPFX": "@JEPFX_1875",
}

# ==================================================
# 💰 CREDIT PRICING
# ==================================================
CREDIT_PRICING = {
    "trial_hour": 2,
    "custom_hour": 2,
    "custom_day": 5,
    "custom_week": 8,
    "custom_month": 50,
    "custom_year": 800,
    "custom_unlimited": 1500,
    "permanent": 500
}

TELEGRAM_CONTACT = "t.me/JEPFX_0"

# ==================================================
# 💾 SAVE / LOAD DATA
# ==================================================
def load_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, VALID_USERS, LICENSE_HISTORY, USER_REQUESTS, CURRENT_THEME
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                TRIAL_LICENSES = data.get("trials", {})
                TRIAL_USERS = data.get("users", {})
                PERMANENT_LICENSES = data.get("permanent_licenses", {})
                CUSTOM_ACTIVATIONS = data.get("custom_activations", {})
                USAGE_LOGS = data.get("usage_logs", {})
                ADMINS = data.get("admins", {})
                MODERATORS = data.get("moderators", {})
                VALID_USERS.update(data.get("valid_users", {}))
                LICENSE_HISTORY = data.get("license_history", [])
                USER_REQUESTS = data.get("user_requests", [])
                CURRENT_THEME = data.get("theme", "dark")
            print(f"✅ DATA LOADED")
        except Exception as e:
            print(f"⚠️ LOAD ERROR: {e}")
            reset_data()
    else:
        reset_data()

def reset_data():
    global TRIAL_LICENSES, TRIAL_USERS, PERMANENT_LICENSES, CUSTOM_ACTIVATIONS, USAGE_LOGS, ADMINS, MODERATORS, LICENSE_HISTORY, USER_REQUESTS
    TRIAL_LICENSES = {}
    TRIAL_USERS = {}
    PERMANENT_LICENSES = {}
    CUSTOM_ACTIVATIONS = {}
    USAGE_LOGS = {}
    ADMINS = {}
    MODERATORS = {}
    LICENSE_HISTORY = []
    USER_REQUESTS = []
    save_data()

def save_data():
    data = {
        "trials": TRIAL_LICENSES,
        "users": TRIAL_USERS,
        "permanent_licenses": PERMANENT_LICENSES,
        "custom_activations": CUSTOM_ACTIVATIONS,
        "usage_logs": USAGE_LOGS,
        "admins": ADMINS,
        "moderators": MODERATORS,
        "valid_users": VALID_USERS,
        "license_history": LICENSE_HISTORY,
        "user_requests": USER_REQUESTS,
        "theme": CURRENT_THEME
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"❌ SAVE ERROR: {e}")

load_data()

# ==================================================
# 📜 LICENSE HISTORY FUNCTION
# ==================================================
def add_to_history(license_key, username, password, license_type, owner, expires_at, details=None):
    history_entry = {
        "license_key": license_key,
        "username": username,
        "password": password,
        "type": license_type,
        "owner": owner,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at,
        "details": details or {}
    }
    LICENSE_HISTORY.append(history_entry)
    save_data()

def get_history_by_owner(owner, role):
    if role == "master":
        return LICENSE_HISTORY
    return [h for h in LICENSE_HISTORY if h.get("owner") == owner]

# ==================================================
# 📊 USAGE TRACKING
# ==================================================
def log_usage(license_key, event_type, details=None):
    if license_key not in USAGE_LOGS:
        USAGE_LOGS[license_key] = []
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details or {}
    }
    
    USAGE_LOGS[license_key].append(log_entry)
    
    if len(USAGE_LOGS[license_key]) > 1000:
        USAGE_LOGS[license_key] = USAGE_LOGS[license_key][-1000:]
    
    save_data()

def get_usage_stats(license_key):
    logs = USAGE_LOGS.get(license_key, [])
    
    stats = {
        "total_usage": len(logs),
        "total_activations": sum(1 for l in logs if l["event_type"] == "activation"),
        "total_verifications": sum(1 for l in logs if l["event_type"] == "verification"),
        "total_logins": sum(1 for l in logs if l["event_type"] == "login"),
        "last_used": logs[-1]["timestamp"] if logs else None,
        "unique_hwids": list(set(l["details"].get("hwid") for l in logs if "hwid" in l["details"]))
    }
    return stats

def check_admin_auth(data):
    username = data.get("admin_username", "")
    password = data.get("admin_password", "")
    
    if username == MASTER_ADMIN["username"] and password == MASTER_ADMIN["password"]:
        return {"authorized": True, "role": "master", "username": username}
    
    if username in ADMINS and ADMINS[username]["password"] == password:
        return {"authorized": True, "role": "admin", "username": username, "credits": ADMINS[username]["credits"]}
    
    if username in MODERATORS and MODERATORS[username]["password"] == password:
        return {"authorized": True, "role": "moderator", "username": username, "credits": MODERATORS[username]["credits"]}
    
    return {"authorized": False}

def deduct_credits(username, amount):
    if username == MASTER_ADMIN["username"]:
        return True
    
    if username in ADMINS:
        if ADMINS[username]["credits"] >= amount:
            ADMINS[username]["credits"] = round(ADMINS[username]["credits"] - amount, 2)
            save_data()
            return True
        return False
    
    if username in MODERATORS:
        if MODERATORS[username]["credits"] >= amount:
            MODERATORS[username]["credits"] = round(MODERATORS[username]["credits"] - amount, 2)
            save_data()
            return True
        return False
    
    return False

def add_credits(username, amount):
    if username in ADMINS:
        ADMINS[username]["credits"] = round(ADMINS[username]["credits"] + amount, 2)
        save_data()
        return True
    if username in MODERATORS:
        MODERATORS[username]["credits"] = round(MODERATORS[username]["credits"] + amount, 2)
        save_data()
        return True
    return False

def get_credits(username):
    if username == MASTER_ADMIN["username"]:
        return "Unlimited"
    if username in ADMINS:
        return ADMINS[username]["credits"]
    if username in MODERATORS:
        return MODERATORS[username]["credits"]
    return 0

def get_licenses_by_owner(owner, role):
    if role == "master":
        return {
            "trials": TRIAL_LICENSES,
            "custom": CUSTOM_ACTIVATIONS,
            "permanent": PERMANENT_LICENSES
        }
    elif role == "admin":
        filtered_trials = {k: v for k, v in TRIAL_LICENSES.items() if v.get("owner") == owner}
        filtered_custom = {k: v for k, v in CUSTOM_ACTIVATIONS.items() if v.get("owner") == owner}
        return {
            "trials": filtered_trials,
            "custom": filtered_custom,
            "permanent": {}
        }
    else:
        filtered_trials = {k: v for k, v in TRIAL_LICENSES.items() if v.get("owner") == owner}
        return {
            "trials": filtered_trials,
            "custom": {},
            "permanent": {}
        }

def find_license_by_credentials(username, password):
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation.get("username") == username and activation.get("password") == password:
            return key, "custom", activation
    
    for user, user_data in TRIAL_USERS.items():
        if user == username and user_data.get("password") == password:
            return user_data.get("linked_license"), "trial", TRIAL_LICENSES.get(user_data.get("linked_license"), {})
    
    for key, lic in PERMANENT_LICENSES.items():
        if lic.get("username") == username and lic.get("password") == password:
            return key, "permanent", lic
    
    return None, None, None

# ==================================================
# 🔍 MONITORING THREAD
# ==================================================
def monitor_expired_licenses():
    while True:
        try:
            now = datetime.utcnow()
            changes_made = False
            
            for key, activation in list(CUSTOM_ACTIVATIONS.items()):
                if activation.get("expires_at") and activation.get("activated", False):
                    exp_time = datetime.fromisoformat(activation["expires_at"])
                    if now > exp_time:
                        del CUSTOM_ACTIVATIONS[key]
                        changes_made = True
            
            for key, lic in list(TRIAL_LICENSES.items()):
                if lic.get("expires_at") and lic.get("activated", False):
                    exp_time = datetime.fromisoformat(lic["expires_at"])
                    if now > exp_time:
                        for user, user_data in list(TRIAL_USERS.items()):
                            if user_data.get("linked_license") == key:
                                del TRIAL_USERS[user]
                        del TRIAL_LICENSES[key]
                        changes_made = True
            
            if changes_made:
                save_data()
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
        time.sleep(60)

monitor_thread = threading.Thread(target=monitor_expired_licenses, daemon=True)
monitor_thread.start()

# ==================================================
# 🎨 ADMIN PANEL HTML
# ==================================================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        """ + get_theme_css() + """
        .container { max-width: 1400px; margin: 0 auto; }
        .login-box { max-width: 400px; margin: 100px auto; padding: 30px; border-radius: 15px; text-align: center; }
        .login-box input { width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 8px; }
        .login-box button { padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .panel { display: none; }
        .header { border-radius: 15px; padding: 20px; margin-bottom: 20px; }
        .result-box { padding: 20px; border-radius: 10px; margin-top: 20px; border-left: 3px solid var(--primary); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; display: block; overflow-x: auto; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
        .master-only { border-left: 3px solid var(--danger); padding: 10px; margin: 10px 0; border-radius: 5px; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; }
        .badge-pending { background: var(--warning); }
        .badge-approved { background: var(--secondary); }
        .badge-rejected { background: var(--danger); }
    </style>
</head>
<body>
<div class="container">
    <div id="loginScreen" class="login-box">
        <h2>🔒 JEPFX ADMIN LOGIN</h2>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="login()">LOGIN</button>
        <p id="loginError" style="color: var(--danger); display: none; margin-top: 10px;">Invalid credentials!</p>
    </div>
    
    <div id="mainPanel" class="panel">
        <div class="header">
            <h1>⚡ JEPFX ADMIN PANEL</h1>
            <p>Welcome, <span id="currentUser">-</span> | Role: <span id="currentRole">-</span> | Credits: <span id="currentCredits">0</span></p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number" id="statTrials">0</div><div>My Trials</div></div>
            <div class="stat-card" id="statCustomCard"><div class="stat-number" id="statCustom">0</div><div>My Custom</div></div>
            <div class="stat-card" id="statPermanentCard" style="display: none;"><div class="stat-number" id="statPermanent">0</div><div>My Permanent</div></div>
            <div class="stat-card"><div class="stat-number" id="statHistory">0</div><div>History</div></div>
            <div class="stat-card"><div class="stat-number" id="statRequests">0</div><div>Requests</div></div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('generateTrial')">🎲 TRIAL</button>
            <button class="tab" id="customTab" onclick="switchTab('customActivation')">✨ CUSTOM</button>
            <button class="tab" id="permanentTab" style="display: none;" onclick="switchTab('permanentLicense')">🔑 PERMANENT</button>
            <button class="tab" onclick="switchTab('myLicenses')">📋 MY LICENSES</button>
            <button class="tab" onclick="switchTab('userRequests')">📨 REQUESTS</button>
            <button class="tab" onclick="switchTab('history')">📜 HISTORY</button>
            <button class="tab" id="adminTab" style="display: none;" onclick="switchTab('admins')">👨‍💼 MANAGE</button>
            <button class="tab" onclick="switchTab('changePassword')">🔐 PASSWORD</button>
            <button class="tab" onclick="switchTab('monitor')">📈 MONITOR</button>
        </div>
        
        <div id="generateTrial" class="content active">
            <h2>🎲 Generate Trial License</h2>
            <select id="trialDuration">
                <option value="3">3 Hours (2 credits)</option>
                <option value="6">6 Hours (3 credits)</option>
                <option value="12">12 Hours (4 credits)</option>
                <option value="24">1 Day (5 credits)</option>
                <option value="72">3 Days (10 credits)</option>
                <option value="168">1 Week (20 credits)</option>
                <option value="720">1 Month (50 credits)</option>
            </select>
            <input type="number" id="maxDevices" placeholder="Max devices (default: 1)" value="1" min="1" max="50">
            <button onclick="generateTrial()">GENERATE LICENSE</button>
            <div id="trialResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="customActivation" class="content">
            <h2>✨ Custom Activation</h2>
            <input type="text" id="customUsername" placeholder="Username">
            <input type="text" id="customPassword" placeholder="Password">
            <input type="text" id="customLicense" placeholder="License Key">
            <select id="customDurationType">
                <option value="hours">Hours</option>
                <option value="days">Days</option>
                <option value="weeks">Weeks</option>
                <option value="months">Months</option>
                <option value="unlimited">Unlimited</option>
            </select>
            <input type="number" id="customDurationValue" placeholder="Duration value">
            <input type="number" id="customMaxDevices" placeholder="Max devices" value="1">
            <button onclick="createCustomActivation()">CREATE</button>
            <div id="customResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="permanentLicense" class="content">
            <h2>🔑 Permanent License</h2>
            <input type="text" id="permLicenseKey" placeholder="License Key">
            <input type="text" id="permUsername" placeholder="Username (optional)">
            <input type="text" id="permPassword" placeholder="Password (optional)">
            <input type="number" id="permMaxDevices" placeholder="Max devices" value="1">
            <button onclick="createPermanentLicense()">CREATE</button>
            <div id="permResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="myLicenses" class="content">
            <h2>📋 My Licenses</h2>
            <div id="myTrialsList"></div>
            <div id="myCustomList" style="display: none;"></div>
            <div id="myPermanentList" style="display: none;"></div>
        </div>
        
        <div id="userRequests" class="content">
            <h2>📨 User Requests</h2>
            <button onclick="loadUserRequests()">REFRESH</button>
            <div id="requestsList"></div>
        </div>
        
        <div id="history" class="content">
            <h2>📜 License History</h2>
            <input type="text" id="historySearch" placeholder="Search..." onkeyup="filterHistory()">
            <button onclick="loadHistory()">REFRESH</button>
            <div id="historyList"></div>
        </div>
        
        <div id="admins" class="content">
            <div class="master-only"><h2>👑 MASTER CONTROL</h2></div>
            <h3>➕ Add Admin/Mod</h3>
            <input type="text" id="newAdminUser" placeholder="Username">
            <input type="password" id="newAdminPass" placeholder="Password">
            <select id="newAdminRole"><option value="admin">Admin</option><option value="moderator">Moderator</option></select>
            <input type="number" id="newAdminCredits" placeholder="Credits" value="100">
            <button onclick="addAdmin()">ADD</button>
            <div id="adminsList"></div>
        </div>
        
        <div id="changePassword" class="content">
            <h2>🔐 Change Password</h2>
            <input type="password" id="oldPassword" placeholder="Current Password">
            <input type="password" id="newPassword" placeholder="New Password">
            <input type="password" id="confirmPassword" placeholder="Confirm Password">
            <button onclick="changePassword()">UPDATE</button>
            <div id="passwordResult" class="result-box" style="display: none;"></div>
        </div>
        
        <div id="monitor" class="content">
            <h2>📈 Monitor</h2>
            <button onclick="loadMonitor()">REFRESH</button>
            <div id="monitorData" class="result-box"></div>
        </div>
    </div>
</div>

<div id="credsModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modalTitle">🔑 License Credentials</h2>
        <div id="modalBody"></div>
        <button class="btn-success" onclick="copyStyledCredentials()">📋 COPY STYLIZED</button>
    </div>
</div>

""" + THEME_SELECTOR_HTML + """

<script>
    let currentUser = null, currentRole = null;
    let lastGenerated = null;
    
    async function login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const res = await fetch('/api/admin/login', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await res.json();
        if(data.success) {
            currentUser = username;
            currentRole = data.role;
            document.getElementById('currentUser').innerHTML = username;
            document.getElementById('currentRole').innerHTML = data.role;
            document.getElementById('currentCredits').innerHTML = data.credits || 'Unlimited';
            if(data.role === 'master') {
                document.getElementById('adminTab').style.display = 'block';
                document.getElementById('permanentTab').style.display = 'block';
                document.getElementById('statPermanentCard').style.display = 'block';
            } else if(data.role === 'admin') {
                document.getElementById('customTab').style.display = 'inline-block';
                document.getElementById('statCustomCard').style.display = 'block';
            }
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainPanel').style.display = 'block';
            loadStats(); loadMyLicenses(); loadHistory(); loadUserRequests();
        } else {
            document.getElementById('loginError').style.display = 'block';
        }
    }
    
    function switchTab(tabId) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tabId).classList.add('active');
        if(tabId === 'myLicenses') loadMyLicenses();
        if(tabId === 'userRequests') loadUserRequests();
        if(tabId === 'history') loadHistory();
        if(tabId === 'admins' && currentRole === 'master') loadAdmins();
        if(tabId === 'monitor') loadMonitor();
    }
    
    async function loadStats() {
        const res = await fetch('/api/admin/get-stats', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        if(data.success) {
            document.getElementById('statTrials').innerHTML = data.trials;
            document.getElementById('statCustom').innerHTML = data.custom || 0;
            document.getElementById('statPermanent').innerHTML = data.permanent || 0;
            document.getElementById('statHistory').innerHTML = data.history_count || 0;
            document.getElementById('statRequests').innerHTML = data.pending_requests || 0;
            document.getElementById('currentCredits').innerHTML = data.user_credits || 'Unlimited';
        }
    }
    
    function formatHours(hours) {
        if(hours >= 720) return Math.floor(hours/720) + ' MONTHS';
        if(hours >= 168) return Math.floor(hours/168) + ' WEEKS';
        if(hours >= 24) return Math.floor(hours/24) + ' DAYS';
        return hours + ' HOURS';
    }
    
    function getStyledText(license, user, pass, duration, devices, type) {
        return `✅ ${type} CREATED\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n🔑 LICENSE: ${license}\\n👤 USER: ${user}\\n🔒 PASS: ${pass}\\n⏱️ TIME: ${duration}\\n💻 MAX DEVICES: ${devices}\\n🌐 CHECK STATUS: jepfx-tool-server.onrender.com/user\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n⚠️ License activates ONLY on first use!`;
    }
    
    function showModal(license, user, pass, duration, devices, type) {
        lastGenerated = {license, user, pass, duration, devices, type};
        const styled = getStyledText(license, user, pass, duration, devices, type);
        document.getElementById('modalBody').innerHTML = `<div class="pre-style">${styled.replace(/\\n/g, '<br>')}</div>`;
        document.getElementById('credsModal').style.display = 'block';
    }
    
    function copyStyledCredentials() {
        if(lastGenerated) {
            const text = getStyledText(lastGenerated.license, lastGenerated.user, lastGenerated.pass, lastGenerated.duration, lastGenerated.devices, lastGenerated.type);
            navigator.clipboard.writeText(text);
            alert('✓ Copied!');
        }
    }
    
    async function generateTrial() {
        const duration = document.getElementById('trialDuration').value;
        const devices = document.getElementById('maxDevices').value;
        const res = await fetch('/api/admin/generate-trial', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, duration_hours: parseInt(duration), max_devices: parseInt(devices)})
        });
        const data = await res.json();
        if(data.success) {
            showModal(data.license_key, data.username, data.password, formatHours(parseInt(duration)), devices, 'TRIAL');
            document.getElementById('trialResult').innerHTML = `✅ Created! Credits used: ${data.credits_used}`;
            loadStats(); loadMyLicenses(); loadHistory();
        } else {
            document.getElementById('trialResult').innerHTML = `❌ ${data.error}`;
        }
        document.getElementById('trialResult').style.display = 'block';
    }
    
    async function createCustomActivation() {
        const username = document.getElementById('customUsername').value;
        const password = document.getElementById('customPassword').value;
        const license = document.getElementById('customLicense').value;
        const durationType = document.getElementById('customDurationType').value;
        const durationValue = document.getElementById('customDurationValue').value;
        const devices = document.getElementById('customMaxDevices').value;
        if(!username || !password || !license) { alert('Fill all fields'); return; }
        const res = await fetch('/api/admin/create-custom-activation', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, username, password, license_key: license, duration_type: durationType, duration_value: parseFloat(durationValue), max_devices: parseInt(devices)})
        });
        const data = await res.json();
        if(data.success) {
            showModal(license, username, password, durationValue + ' ' + durationType, devices, 'CUSTOM');
            document.getElementById('customResult').innerHTML = `✅ Created!`;
            loadStats(); loadMyLicenses(); loadHistory();
        } else {
            document.getElementById('customResult').innerHTML = `❌ ${data.error}`;
        }
        document.getElementById('customResult').style.display = 'block';
    }
    
    async function createPermanentLicense() {
        const license = document.getElementById('permLicenseKey').value;
        const username = document.getElementById('permUsername').value;
        const password = document.getElementById('permPassword').value;
        const devices = document.getElementById('permMaxDevices').value;
        if(!license) { alert('License key required'); return; }
        const res = await fetch('/api/admin/create-permanent-license', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, license_key: license, username, password, max_devices: parseInt(devices)})
        });
        const data = await res.json();
        if(data.success) {
            showModal(license, username || 'N/A', password || 'N/A', 'PERMANENT', devices, 'PERMANENT');
            document.getElementById('permResult').innerHTML = `✅ Created!`;
            loadStats(); loadMyLicenses(); loadHistory();
        } else {
            document.getElementById('permResult').innerHTML = `❌ ${data.error}`;
        }
        document.getElementById('permResult').style.display = 'block';
    }
    
    async function loadMyLicenses() {
        const res = await fetch('/api/admin/get-my-trials', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '<table><tr><th>License</th><th>Max Devices</th><th>Used</th><th>Activated</th><th>Expires</th><th>Status</th><th>Action</th></tr>';
        data.trials.forEach(t => {
            html += `<tr><td>${t.license_key}</td><td>${t.max_devices}</td><td>${t.hwid_count}</td><td>${t.activated ? '✅' : '⏳'}</td><td>${t.expires_at}</td><td>${t.status}</td><td><button class="btn-danger" onclick="deleteTrial('${t.license_key}')">Delete</button></td></tr>`;
        });
        html += '</table>';
        document.getElementById('myTrialsList').innerHTML = html;
    }
    
    async function loadHistory() {
        const res = await fetch('/api/admin/get-history', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '能懈<tr><th>Created</th><th>License</th><th>Username</th><th>Password</th><th>Type</th><th>Owner</th><th>Expires</th><th>Action</th></tr>';
        data.history.forEach(h => {
            html += `<tr><td>${new Date(h.created_at).toLocaleString()}</td><td>${h.license_key}</td><td>${h.username}</td><td>${h.password}</td><td>${h.type}</td><td>${h.owner}</td><td>${h.expires_at}</td><td><button onclick="showHistoryCreds('${h.license_key}', '${h.username}', '${h.password}', '${h.type}')">View</button></td></tr>`;
        });
        html += '</table>';
        document.getElementById('historyList').innerHTML = html;
    }
    
    function showHistoryCreds(license, user, pass, type) {
        const styled = `📜 HISTORY LICENSE\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n🔑 LICENSE: ${license}\\n👤 USER: ${user}\\n🔒 PASS: ${pass}\\n📋 TYPE: ${type}\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;
        document.getElementById('modalBody').innerHTML = `<div class="pre-style">${styled.replace(/\\n/g, '<br>')}</div>`;
        document.getElementById('credsModal').style.display = 'block';
    }
    
    function filterHistory() {
        const search = document.getElementById('historySearch').value.toLowerCase();
        const rows = document.querySelectorAll('#historyList tr');
        rows.forEach((row, i) => { if(i > 0) row.style.display = row.textContent.toLowerCase().includes(search) ? '' : 'none'; });
    }
    
    async function loadUserRequests() {
        const res = await fetch('/api/admin/get-requests', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '能懈<tr><th>Date</th><th>License</th><th>User</th><th>Type</th><th>Message</th><th>Status</th><th>Action</th></tr>';
        data.requests.forEach((req, idx) => {
            html += `<tr><td>${new Date(req.created_at).toLocaleString()}</td><td>${req.license_key}</td><td>${req.username}</td><td>${req.request_type}</td><td>${req.message.substring(0, 50)}</td><td><span class="badge badge-${req.status}">${req.status}</span></td><td>${req.status === 'pending' ? `<button class="btn-success" onclick="approveRequest(${idx})">Approve</button> <button class="btn-danger" onclick="rejectRequest(${idx})">Reject</button>` : '-'}</td></tr>`;
        });
        html += '</table>';
        document.getElementById('requestsList').innerHTML = html;
    }
    
    async function approveRequest(idx) {
        const res = await fetch('/api/admin/approve-request', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, request_index: idx})
        });
        if((await res.json()).success) { loadUserRequests(); loadStats(); alert('Approved!'); }
    }
    
    async function rejectRequest(idx) {
        const res = await fetch('/api/admin/reject-request', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, request_index: idx})
        });
        if((await res.json()).success) { loadUserRequests(); alert('Rejected!'); }
    }
    
    async function loadAdmins() {
        const res = await fetch('/api/admin/get-admins', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        let html = '能懈<tr><th>Username</th><th>Credits</th><th>Action</th></tr>';
        data.admins.forEach(a => { html += `<tr><td>${a.username}</td><td>${a.credits}</td><td><button class="btn-danger" onclick="deleteAdmin('${a.username}')">Delete</button></td></tr>`; });
        html += '</table>';
        document.getElementById('adminsList').innerHTML = html;
    }
    
    async function addAdmin() {
        const username = document.getElementById('newAdminUser').value;
        const password = document.getElementById('newAdminPass').value;
        const role = document.getElementById('newAdminRole').value;
        const credits = document.getElementById('newAdminCredits').value;
        const res = await fetch('/api/admin/add-admin', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value, new_username: username, new_password: password, role: role, credits: parseFloat(credits)})
        });
        if((await res.json()).success) { loadAdmins(); alert('Added!'); }
    }
    
    async function changePassword() {
        const oldPass = document.getElementById('oldPassword').value;
        const newPass = document.getElementById('newPassword').value;
        const confirmPass = document.getElementById('confirmPassword').value;
        if(newPass !== confirmPass) { alert('Passwords do not match'); return; }
        const res = await fetch('/api/admin/change-password', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: currentUser, old_password: oldPass, new_password: newPass})
        });
        const data = await res.json();
        if(data.success) { alert('Password changed! Please login again.'); location.reload(); }
        else { alert(data.error); }
    }
    
    async function loadMonitor() {
        const res = await fetch('/api/admin/get-monitor-data', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({admin_username: currentUser, admin_password: document.getElementById('loginPassword').value})
        });
        const data = await res.json();
        document.getElementById('monitorData').innerHTML = `Trials: ${data.my_trials}<br>Custom: ${data.my_custom}<br>Permanent: ${data.my_permanent}<br>History: ${data.history_count}<br>Pending: ${data.pending_requests}<br>Active Users: ${data.active_users}<br><br>${data.server_time}`;
    }
    
    async function deleteTrial(key) {
        if(confirm('Delete?')) {
            await fetch('/api/admin/delete-trial', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_username:currentUser, admin_password:document.getElementById('loginPassword').value, license_key:key})});
            loadMyLicenses(); loadStats();
        }
    }
    
    async function deleteAdmin(username) {
        if(confirm(`Delete ${username}?`)) {
            await fetch('/api/admin/delete-admin', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({admin_username:currentUser, admin_password:document.getElementById('loginPassword').value, target_username:username, role:'admin'})});
            loadAdmins();
        }
    }
    
    function closeModal() { document.getElementById('credsModal').style.display = 'none'; }
    setInterval(() => { if(document.getElementById('mainPanel').style.display === 'block') loadStats(); }, 30000);
</script>
</body>
</html>
"""

# ==================================================
# 🎨 USER PORTAL HTML
# ==================================================
USER_PORTAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JEPFX License Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        """ + get_theme_css() + """
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: var(--primary); }
        .card { background: var(--card-bg); backdrop-filter: blur(10px); border-radius: 15px; padding: 25px; margin-bottom: 20px; }
        .card h2 { color: var(--primary); margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid var(--border); border-radius: 8px; background: var(--input-bg); color: var(--text); }
        button { background: var(--primary); color: white; padding: 12px 25px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .status-box { border-radius: 10px; padding: 15px; margin: 15px 0; border-left: 3px solid var(--primary); }
        .status-active { border-left-color: var(--secondary); }
        .status-expired { border-left-color: var(--danger); }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); }
        .info-label { color: var(--text-secondary); }
        .info-value { color: var(--text); font-weight: bold; }
        .contact-buttons { display: flex; gap: 10px; margin-top: 20px; }
        .telegram-btn { background: #0088cc; text-decoration: none; color: white; padding: 12px; border-radius: 8px; text-align: center; }
        .request-form { display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); }
        .request-form.show { display: block; }
        .alert-error { background: rgba(239,68,68,0.2); border: 1px solid var(--danger); padding: 12px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: rgba(59,130,246,0.2); border: 1px solid var(--primary); padding: 12px; border-radius: 8px; margin: 10px 0; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .badge-active { background: var(--secondary); color: white; }
        .badge-expired { background: var(--danger); color: white; }
        .hidden { display: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔑 JEPFX License Portal</h1>
        <p>Check your license status, request extensions, and get support</p>
    </div>
    
    <div id="loginSection" class="card">
        <h2>🔐 License Login</h2>
        <input type="text" id="loginUsername" placeholder="Username">
        <input type="password" id="loginPassword" placeholder="Password">
        <button onclick="checkLicense()">CHECK LICENSE</button>
        <div id="loginError" class="alert-error" style="display: none;"></div>
    </div>
    
    <div id="statusSection" class="card hidden">
        <div id="statusContent"></div>
        <div id="requestForm" class="request-form">
            <h3>📨 Request Extension</h3>
            <textarea id="requestMessage" rows="3" placeholder="Describe your request..."></textarea>
            <input type="text" id="contactInfo" placeholder="Your contact (Telegram)" value="t.me/">
            <button onclick="submitRequest()">SUBMIT</button>
            <div id="requestResult" class="alert-info" style="display: none;"></div>
        </div>
        <div class="contact-buttons">
            <a href="https://t.me/JEPFX_0" target="_blank" class="telegram-btn">📱 Contact on Telegram</a>
        </div>
    </div>
</div>

""" + THEME_SELECTOR_HTML + """

<script>
    let currentLicenseKey = null;
    let currentUsername = null;
    
    async function checkLicense() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        if(!username || !password) { showError('Enter username and password'); return; }
        
        const res = await fetch('/api/user/check-license', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await res.json();
        if(data.success) {
            currentLicenseKey = data.license_key;
            currentUsername = username;
            displayStatus(data);
            document.getElementById('loginSection').classList.add('hidden');
            document.getElementById('statusSection').classList.remove('hidden');
        } else {
            showError(data.error);
        }
    }
    
    function displayStatus(data) {
        const statusClass = data.is_expired ? 'status-expired' : 'status-active';
        const badgeClass = data.is_expired ? 'badge-expired' : 'badge-active';
        const statusText = data.is_expired ? 'EXPIRED' : 'ACTIVE';
        
        let activationMsg = '';
        if(!data.activated && data.license_type === 'trial') {
            activationMsg = '<div class="alert-info">⏳ Not activated yet. Countdown starts on first use!</div>';
        }
        
        const html = `
            <div class="status-box ${statusClass}">
                <div class="info-row"><span class="info-label">🔑 License:</span><span class="info-value">${data.license_key}</span></div>
                <div class="info-row"><span class="info-label">👤 Username:</span><span class="info-value">${data.username}</span></div>
                <div class="info-row"><span class="info-label">📋 Type:</span><span class="info-value">${data.license_type}</span></div>
                <div class="info-row"><span class="info-label">📅 Expires:</span><span class="info-value">${data.expires_at || 'NEVER'}</span></div>
                <div class="info-row"><span class="info-label">⏰ Status:</span><span class="info-value"><span class="badge ${badgeClass}">${statusText}</span></span></div>
                ${data.days_left ? `<div class="info-row"><span class="info-label">📆 Days Left:</span><span class="info-value">${data.days_left}</span></div>` : ''}
                ${data.max_devices ? `<div class="info-row"><span class="info-label">💻 Max Devices:</span><span class="info-value">${data.max_devices}</span></div>` : ''}
            </div>
            ${activationMsg}
        `;
        document.getElementById('statusContent').innerHTML = html;
        document.getElementById('requestForm').classList.add('show');
    }
    
    async function submitRequest() {
        const message = document.getElementById('requestMessage').value;
        const contact = document.getElementById('contactInfo').value;
        if(!message) { alert('Please describe your request'); return; }
        
        const res = await fetch('/api/user/submit-request', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({license_key: currentLicenseKey, username: currentUsername, request_type: 'extension', message, contact})
        });
        const data = await res.json();
        const resultDiv = document.getElementById('requestResult');
        if(data.success) {
            resultDiv.innerHTML = '✅ Request submitted! Admin will review it.';
            resultDiv.style.display = 'block';
            document.getElementById('requestMessage').value = '';
        } else {
            resultDiv.innerHTML = '❌ Error: ' + data.error;
            resultDiv.style.display = 'block';
        }
    }
    
    function showError(msg) {
        const errorDiv = document.getElementById('loginError');
        errorDiv.innerHTML = msg;
        errorDiv.style.display = 'block';
        setTimeout(() => errorDiv.style.display = 'none', 5000);
    }
</script>
</body>
</html>
"""

# ==================================================
# 🔐 API ENDPOINTS
# ==================================================

@app.route('/api/set-theme', methods=['POST'])
def set_theme():
    global CURRENT_THEME
    data = request.get_json()
    theme = data.get("theme", "dark")
    if theme in THEMES:
        CURRENT_THEME = theme
        save_data()
    return jsonify({"success": True})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    if username == MASTER_ADMIN["username"] and password == MASTER_ADMIN["password"]:
        return jsonify({"success": True, "role": "master", "credits": "Unlimited"}), 200
    
    if username in ADMINS and ADMINS[username]["password"] == password:
        return jsonify({"success": True, "role": "admin", "credits": ADMINS[username]["credits"]}), 200
    
    if username in MODERATORS and MODERATORS[username]["password"] == password:
        return jsonify({"success": True, "role": "moderator", "credits": MODERATORS[username]["credits"]}), 200
    
    return jsonify({"success": False}), 401

@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    data = request.get_json()
    username = data.get("username", "")
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if username == MASTER_ADMIN["username"]:
        if old_password == MASTER_ADMIN["password"]:
            MASTER_ADMIN["password"] = new_password
            save_data()
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Wrong password"}), 401
    
    if username in ADMINS:
        if ADMINS[username]["password"] == old_password:
            ADMINS[username]["password"] = new_password
            save_data()
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Wrong password"}), 401
    
    if username in MODERATORS:
        if MODERATORS[username]["password"] == old_password:
            MODERATORS[username]["password"] = new_password
            save_data()
            return jsonify({"success": True}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/get-stats', methods=['POST'])
def get_stats():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    licenses = get_licenses_by_owner(auth["username"], auth["role"])
    history = get_history_by_owner(auth["username"], auth["role"])
    pending_requests = sum(1 for r in USER_REQUESTS if r.get("status") == "pending")
    
    return jsonify({
        "success": True,
        "trials": len(licenses["trials"]),
        "custom": len(licenses["custom"]),
        "permanent": len(licenses["permanent"]),
        "history_count": len(history),
        "pending_requests": pending_requests,
        "user_credits": auth.get("credits", "Unlimited")
    }), 200

@app.route('/api/admin/generate-trial', methods=['POST'])
def generate_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    dur = int(data.get("duration_hours", 3))
    max_devices = int(data.get("max_devices", 1))
    credits_cost = round(dur * 0.1, 2)
    
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], credits_cost):
            return jsonify({"success": False, "error": f"Insufficient credits. Need {credits_cost} credits"}), 400
    
    lic = f"JEPFX-TRIAL-{uuid.uuid4().hex[:8].upper()}"
    user = f"TRIAL-{uuid.uuid4().hex[:6].upper()}"
    pwd = uuid.uuid4().hex[:10].upper()
    
    TRIAL_LICENSES[lic] = {
        "type": "trial",
        "owner": auth["username"],
        "hwids": [],
        "max_devices": max_devices,
        "duration_hours": dur,
        "start_time": None,
        "expires_at": None,
        "activated": False,
        "created_at": datetime.utcnow().isoformat()
    }
    TRIAL_USERS[user] = {"password": pwd, "linked_license": lic}
    
    add_to_history(lic, user, pwd, "Trial", auth["username"], "NOT ACTIVATED YET", {"duration_hours": dur, "max_devices": max_devices})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "license_key": lic,
        "username": user,
        "password": pwd,
        "credits_used": credits_cost,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/create-custom-activation', methods=['POST'])
def create_custom_activation():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] == "moderator":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    license_key = data.get("license_key", "").strip().upper()
    duration_type = data.get("duration_type", "hours")
    duration_value = float(data.get("duration_value", 0))
    max_devices = int(data.get("max_devices", 1))
    
    if not username or not password or not license_key:
        return jsonify({"success": False, "error": "Missing fields"}), 400
    
    now = datetime.utcnow()
    expires_at = None
    credits_cost = 0
    
    if duration_type == "hours":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_hour"], 2)
        expires_at = now + timedelta(hours=duration_value)
    elif duration_type == "days":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_day"], 2)
        expires_at = now + timedelta(days=duration_value)
    elif duration_type == "weeks":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_week"], 2)
        expires_at = now + timedelta(weeks=duration_value)
    elif duration_type == "months":
        credits_cost = round(duration_value * CREDIT_PRICING["custom_month"], 2)
        expires_at = now + timedelta(days=duration_value * 30)
    elif duration_type == "unlimited":
        credits_cost = CREDIT_PRICING["custom_unlimited"]
        expires_at = None
    
    if auth["role"] != "master":
        if not deduct_credits(auth["username"], credits_cost):
            return jsonify({"success": False, "error": f"Insufficient credits"}), 400
    
    CUSTOM_ACTIVATIONS[license_key] = {
        "username": username,
        "password": password,
        "license_key": license_key,
        "owner": auth["username"],
        "hwids": [],
        "max_devices": max_devices,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": now.isoformat(),
        "activated": False
    }
    
    VALID_USERS[username] = password
    add_to_history(license_key, username, password, "Custom", auth["username"], expires_at.isoformat() if expires_at else "UNLIMITED", {"max_devices": max_devices})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "expires_at": expires_at.isoformat() if expires_at else "NEVER",
        "credits_used": credits_cost,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/create-permanent-license', methods=['POST'])
def create_permanent_license():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    license_key = data.get("license_key", "").strip().upper()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    max_devices = int(data.get("max_devices", 1))
    
    if not license_key:
        return jsonify({"success": False, "error": "License key required"}), 400
    
    PERMANENT_LICENSES[license_key] = {
        "type": "permanent",
        "owner": auth["username"],
        "username": username if username else None,
        "password": password if password else None,
        "hwids": [],
        "max_devices": max_devices,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if username and password:
        VALID_USERS[username] = password
    
    add_to_history(license_key, username if username else "N/A", password if password else "N/A", "Permanent", auth["username"], "NEVER", {"max_devices": max_devices})
    
    save_data()
    remaining = get_credits(auth["username"])
    
    return jsonify({
        "success": True,
        "remaining_credits": remaining
    }), 200

@app.route('/api/admin/get-my-trials', methods=['POST'])
def get_my_trials():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    now = datetime.utcnow()
    list_trials = []
    
    for k, v in TRIAL_LICENSES.items():
        if v.get("owner") == auth["username"] or auth["role"] == "master":
            status = "AWAITING"
            activated = False
            if v.get("activated"):
                activated = True
                if v.get("expires_at"):
                    exp = datetime.fromisoformat(v["expires_at"])
                    if exp > now:
                        status = "ACTIVE"
                    else:
                        status = "EXPIRED"
            
            list_trials.append({
                "license_key": k,
                "max_devices": v.get("max_devices", 1),
                "hwid_count": len(v.get("hwids", [])),
                "activated": activated,
                "expires_at": v.get("expires_at") or "Not activated",
                "status": status
            })
    
    return jsonify({"trials": list_trials}), 200

@app.route('/api/admin/get-history', methods=['POST'])
def get_history():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    history = get_history_by_owner(auth["username"], auth["role"])
    history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({"history": history}), 200

@app.route('/api/admin/get-admins', methods=['POST'])
def get_admins():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    admins_list = [{"username": k, "credits": v["credits"]} for k, v in ADMINS.items()]
    return jsonify({"admins": admins_list}), 200

@app.route('/api/admin/add-admin', methods=['POST'])
def add_admin():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    new_username = data.get("new_username", "")
    new_password = data.get("new_password", "")
    role = data.get("role", "admin")
    credits = float(data.get("credits", 100))
    
    if not new_username or not new_password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    
    if role == "admin":
        ADMINS[new_username] = {"password": new_password, "credits": credits, "created_at": datetime.utcnow().isoformat()}
    else:
        MODERATORS[new_username] = {"password": new_password, "credits": credits, "created_at": datetime.utcnow().isoformat()}
    
    save_data()
    return jsonify({"success": True}), 200

@app.route('/api/admin/delete-admin', methods=['POST'])
def delete_admin():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"] or auth["role"] != "master":
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    target_username = data.get("target_username", "")
    role = data.get("role", "admin")
    
    if role == "admin" and target_username in ADMINS:
        del ADMINS[target_username]
        save_data()
        return jsonify({"success": True}), 200
    
    if role == "moderator" and target_username in MODERATORS:
        del MODERATORS[target_username]
        save_data()
        return jsonify({"success": True}), 200
    
    return jsonify({"success": False, "error": "User not found"}), 404

@app.route('/api/admin/get-monitor-data', methods=['POST'])
def get_monitor_data():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    licenses = get_licenses_by_owner(auth["username"], auth["role"])
    history = get_history_by_owner(auth["username"], auth["role"])
    pending_requests = sum(1 for r in USER_REQUESTS if r.get("status") == "pending")
    
    active_users = set()
    for logs in USAGE_LOGS.values():
        for log in logs[-10:]:
            if "hwid" in log.get("details", {}):
                active_users.add(log["details"]["hwid"])
    
    return jsonify({
        "my_trials": len(licenses["trials"]),
        "my_custom": len(licenses["custom"]),
        "my_permanent": len(licenses["permanent"]),
        "history_count": len(history),
        "pending_requests": pending_requests,
        "active_users": len(active_users),
        "server_time": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/admin/delete-trial', methods=['POST'])
def delete_trial():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    key = data.get("license_key", "")
    
    if key in TRIAL_LICENSES:
        if auth["role"] != "master" and TRIAL_LICENSES[key].get("owner") != auth["username"]:
            return jsonify({"success": False, "error": "Not your license"}), 403
        
        for user, user_data in list(TRIAL_USERS.items()):
            if user_data.get("linked_license") == key:
                del TRIAL_USERS[user]
        del TRIAL_LICENSES[key]
        save_data()
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/admin/get-requests', methods=['POST'])
def admin_get_requests():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    if auth["role"] == "master":
        requests = USER_REQUESTS
    else:
        owned_licenses = set()
        for k in TRIAL_LICENSES:
            if TRIAL_LICENSES[k].get("owner") == auth["username"]:
                owned_licenses.add(k)
        for k in CUSTOM_ACTIVATIONS:
            if CUSTOM_ACTIVATIONS[k].get("owner") == auth["username"]:
                owned_licenses.add(k)
        requests = [r for r in USER_REQUESTS if r.get("license_key") in owned_licenses]
    
    requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"requests": requests}), 200

@app.route('/api/admin/approve-request', methods=['POST'])
def admin_approve_request():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    req_index = data.get("request_index")
    
    if req_index is None or req_index >= len(USER_REQUESTS):
        return jsonify({"success": False, "error": "Request not found"}), 404
    
    USER_REQUESTS[req_index]["status"] = "approved"
    USER_REQUESTS[req_index]["approved_at"] = datetime.utcnow().isoformat()
    
    save_data()
    return jsonify({"success": True}), 200

@app.route('/api/admin/reject-request', methods=['POST'])
def admin_reject_request():
    data = request.get_json()
    auth = check_admin_auth(data)
    if not auth["authorized"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    req_index = data.get("request_index")
    
    if req_index is None or req_index >= len(USER_REQUESTS):
        return jsonify({"success": False, "error": "Request not found"}), 404
    
    USER_REQUESTS[req_index]["status"] = "rejected"
    USER_REQUESTS[req_index]["rejected_at"] = datetime.utcnow().isoformat()
    
    save_data()
    return jsonify({"success": True}), 200

# ==================================================
# 👥 USER PORTAL ENDPOINTS
# ==================================================

@app.route('/user')
def user_portal():
    return render_template_string(USER_PORTAL_HTML)

@app.route('/api/user/check-license', methods=['POST'])
def user_check_license():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    license_key, license_type, license_data = find_license_by_credentials(username, password)
    
    if not license_key:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    
    now = datetime.utcnow()
    expires_at = license_data.get("expires_at")
    is_expired = False
    days_left = None
    activated = license_data.get("activated", False)
    
    if license_type == "trial" and not activated:
        days_left = None
        is_expired = False
    elif expires_at and expires_at not in ["NEVER", "UNLIMITED", "NOT ACTIVATED YET"]:
        try:
            exp_time = datetime.fromisoformat(expires_at)
            if now > exp_time:
                is_expired = True
            else:
                days_left = round((exp_time - now).days, 1)
        except:
            pass
    
    return jsonify({
        "success": True,
        "license_key": license_key,
        "username": username,
        "license_type": license_type,
        "expires_at": expires_at if expires_at else ("Not activated yet" if not activated else "NEVER"),
        "is_expired": is_expired,
        "days_left": days_left,
        "activated": activated,
        "max_devices": license_data.get("max_devices", 1),
        "hwids": license_data.get("hwids", [])
    }), 200

@app.route('/api/user/submit-request', methods=['POST'])
def user_submit_request():
    data = request.get_json()
    license_key = data.get("license_key", "")
    username = data.get("username", "")
    request_type = data.get("request_type", "extension")
    message = data.get("message", "")
    contact = data.get("contact", "")
    
    if not license_key or not username or not message:
        return jsonify({"success": False, "error": "Missing fields"}), 400
    
    USER_REQUESTS.append({
        "license_key": license_key,
        "username": username,
        "request_type": request_type,
        "message": message,
        "contact": contact,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })
    save_data()
    
    return jsonify({"success": True}), 200

# ==================================================
# 🔑 ACTIVATION ENDPOINTS
# ==================================================

@app.route('/api/activate', methods=['POST'])
def activate():
    data = request.get_json()
    key = data.get("license_key", "").strip().upper()
    hwid = data.get("hardware_id", "").strip()
    now = datetime.utcnow()
    
    if key in CUSTOM_ACTIVATIONS:
        activation = CUSTOM_ACTIVATIONS[key]
        
        if activation.get("expires_at") and activation.get("activated", False):
            exp_time = datetime.fromisoformat(activation["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        if "hwids" not in activation:
            activation["hwids"] = []
        
        max_devices = activation.get("max_devices", 1)
        if hwid not in activation["hwids"] and len(activation["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        
        if hwid not in activation["hwids"]:
            activation["hwids"].append(hwid)
        
        if not activation.get("activated"):
            activation["activated"] = True
            activation["activated_at"] = now.isoformat()
        
        save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
    if key in PERMANENT_LICENSES:
        lic = PERMANENT_LICENSES[key]
        if "hwids" not in lic:
            lic["hwids"] = []
        max_devices = lic.get("max_devices", 1)
        if hwid not in lic["hwids"] and len(lic["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
            save_data()
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
    if key in TRIAL_LICENSES:
        lic = TRIAL_LICENSES[key]
        if "hwids" not in lic:
            lic["hwids"] = []
        
        max_devices = lic.get("max_devices", 1)
        if hwid not in lic["hwids"] and len(lic["hwids"]) >= max_devices:
            return jsonify({"status": "blocked", "msg": f"Max devices reached ({max_devices})"}), 403
        
        if not lic.get("activated"):
            lic["activated"] = True
            lic["activated_at"] = now.isoformat()
            duration_hours = lic.get("duration_hours", 3)
            expires_at = now + timedelta(hours=duration_hours)
            lic["expires_at"] = expires_at.isoformat()
        
        if hwid not in lic["hwids"]:
            lic["hwids"].append(hwid)
        save_data()
        
        if lic.get("expires_at"):
            exp_time = datetime.fromisoformat(lic["expires_at"])
            if now > exp_time:
                return jsonify({"status": "expired"}), 403
        
        log_usage(key, "activation", {"hwid": hwid})
        return jsonify({"status": "activated"}), 200
    
    return jsonify({"status": "invalid"}), 403

@app.route('/api/verify-license', methods=['POST'])
def verify():
    data = request.get_json()
    hwid = data.get("hwid", "")
    key_hash = data.get("hash", "")
    now = datetime.utcnow()
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if activation.get("expires_at") and activation.get("activated", False):
                exp_time = datetime.fromisoformat(activation["expires_at"])
                if now > exp_time:
                    return jsonify({"expired": True}), 403
            if hwid in activation.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    for key, lic in PERMANENT_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if hwid in lic.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    for key, lic in TRIAL_LICENSES.items():
        if hashlib.sha256(key.encode()).hexdigest() == key_hash:
            if lic.get("expires_at") and lic.get("activated", False):
                exp_time = datetime.fromisoformat(lic["expires_at"])
                if now > exp_time:
                    return jsonify({"expired": True}), 403
            if hwid in lic.get("hwids", []):
                log_usage(key, "verification", {"hwid": hwid})
                return jsonify({"ok": True}), 200
            return jsonify({"invalid": True}), 403
    
    return jsonify({"invalid": True}), 403

@app.route('/api/validate-user', methods=['POST'])
def validate_user():
    username = request.get_json().get("username", "")
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username:
            log_usage(key, "validation", {"username": username})
            return jsonify({"ok": True}), 200
    
    if username in VALID_USERS or username in TRIAL_USERS:
        return jsonify({"ok": True}), 200
    
    return "", 403

@app.route('/api/check-password', methods=['POST'])
def check_pass():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    for key, activation in CUSTOM_ACTIVATIONS.items():
        if activation["username"] == username and activation["password"] == password:
            log_usage(key, "login", {"username": username})
            return jsonify({"ok": True}), 200
    
    if (username in VALID_USERS and VALID_USERS[username] == password) or \
       (username in TRIAL_USERS and TRIAL_USERS[username]["password"] == password):
        return jsonify({"ok": True}), 200
    
    return "", 403

# ==================================================
# 🚀 ROUTES
# ==================================================

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_HTML)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "JEPFX License Server Running",
        "endpoints": {
            "activate": "/api/activate",
            "verify": "/api/verify-license",
            "validate_user": "/api/validate-user",
            "check_password": "/api/check-password",
            "admin_panel": "/admin",
            "user_portal": "/user"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)