from flask import Flask, request, jsonify
import sqlite3
import hashlib
import os

app = Flask(__name__)

# ==============================
# DATABASE
# ==============================
DB = "users.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            banned INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==============================
# HASH PASSWORD
# ==============================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ==============================
# REGISTER
# ==============================
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"status": "error", "msg": "missing fields"})

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute(
            "INSERT INTO users (username, password, banned) VALUES (?, ?, 0)",
            (username, hash_pw(password))
        )

        conn.commit()
        conn.close()

        return jsonify({"status": "success"})

    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "msg": "user exists"})

    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        username = data.get("username")
        password = data.get("password")

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("SELECT password, banned FROM users WHERE username=?", (username,))
        result = c.fetchone()

        conn.close()

        if not result:
            return jsonify({"status": "fail"})

        stored_pw, banned = result

        if banned == 1:
            return jsonify({"status": "error", "msg": "banned"})

        if stored_pw == hash_pw(password):
            return jsonify({"status": "ok"})

        return jsonify({"status": "fail"})

    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# ==============================
# START SERVER (CLOUD SAFE)
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)