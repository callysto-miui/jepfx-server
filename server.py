from flask import Flask, request, jsonify
import sqlite3
import hashlib
import uuid

app = Flask(__name__)

DB = "users.db"

# ==============================
# INIT DB
# ==============================
def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        license TEXT,
        device_id TEXT,
        banned INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init()

# ==============================
# HASH
# ==============================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ==============================
# REGISTER (AUTO LICENSE)
# ==============================
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "msg": "missing fields"})

    license_key = str(uuid.uuid4())[:8]  # simple license

    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("""
        INSERT INTO users (username, password, license, banned)
        VALUES (?, ?, ?, 0)
        """, (username, hash_pw(password), license_key))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "license": license_key})

    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "msg": "user exists"})

# ==============================
# LOGIN (DEVICE LOCK + BAN CHECK)
# ==============================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")
    device_id = data.get("device_id")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT password, banned, device_id FROM users WHERE username=?", (username,))
    user = c.fetchone()

    conn.close()

    if not user:
        return jsonify({"status": "fail"})

    stored_pw, banned, saved_device = user

    if banned == 1:
        return jsonify({"status": "error", "msg": "banned"})

    if stored_pw != hash_pw(password):
        return jsonify({"status": "fail"})

    # DEVICE BINDING
    if saved_device is None:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET device_id=? WHERE username=?", (device_id, username))
        conn.commit()
        conn.close()

    elif saved_device != device_id:
        return jsonify({"status": "error", "msg": "device_locked"})

    return jsonify({"status": "ok"})

# ==============================
# SIMPLE ADMIN VIEW (LEVEL 2 BASIC)
# ==============================
@app.route("/admin/users", methods=["GET"])
def users():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT username, license, banned FROM users")
    data = c.fetchall()

    conn.close()

    return jsonify(data)

# ==============================
# BAN USER
# ==============================
@app.route("/admin/ban", methods=["POST"])
def ban():
    data = request.get_json()
    username = data.get("username")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE users SET banned=1 WHERE username=?", (username,))
    conn.commit()
    conn.close()

    return jsonify({"status": "banned"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
