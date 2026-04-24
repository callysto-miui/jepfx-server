from flask import Flask, request, jsonify
import sqlite3
import hashlib
import os

app = Flask(__name__)

DB = "users.db"

# =========================
# INIT DATABASE
# =========================
def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT UNIQUE,
        password TEXT,
        banned INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "msg": "missing fields"})

    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute(
            "INSERT INTO users VALUES (?, ?, 0)",
            (username, hash_pw(password))
        )

        conn.commit()
        conn.close()

        return jsonify({"status": "success"})

    except:
        return jsonify({"status": "error", "msg": "user exists"})


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT password, banned FROM users WHERE username=?", (username,))
    user = c.fetchone()

    conn.close()

    if not user:
        return jsonify({"status": "fail"})

    stored_pw, banned = user

    if banned == 1:
        return jsonify({"status": "error", "msg": "banned"})

    if stored_pw != hash_pw(password):
        return jsonify({"status": "fail"})

    return jsonify({"status": "ok"})


# =========================
# ADMIN DASHBOARD (WEB UI)
# =========================
@app.route("/admin")
def admin_panel():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT username, banned FROM users")
    users = c.fetchall()

    conn.close()

    html = """
    <html>
    <head>
        <title>JEPFX ADMIN</title>
        <style>
            body { font-family: Arial; background:#0b1220; color:white; }
            table { width:60%; margin:auto; margin-top:50px; border-collapse: collapse; }
            th, td { padding:10px; border:1px solid #333; text-align:center; }
            button { padding:6px 12px; cursor:pointer; border:none; }
            .ban { background:red; color:white; }
            .unban { background:green; color:white; }
        </style>
    </head>
    <body>
        <h2 style="text-align:center;">JEPFX ADMIN PANEL</h2>
        <table>
            <tr><th>Username</th><th>Status</th><th>Action</th></tr>
    """

    for u in users:
        username = u[0]
        banned = u[1]

        if banned == 1:
            html += f"""
            <tr>
                <td>{username}</td>
                <td>BANNED</td>
                <td>
                    <form action="/admin/unban" method="post">
                        <input type="hidden" name="username" value="{username}">
                        <button class="unban">UNBAN</button>
                    </form>
                </td>
            </tr>
            """
        else:
            html += f"""
            <tr>
                <td>{username}</td>
                <td>ACTIVE</td>
                <td>
                    <form action="/admin/ban" method="post">
                        <input type="hidden" name="username" value="{username}">
                        <button class="ban">BAN</button>
                    </form>
                </td>
            </tr>
            """

    html += "</table></body></html>"
    return html


# =========================
# BAN USER (FIXED FOR HTML FORM)
# =========================
@app.route("/admin/ban", methods=["POST"])
def ban_user():
    username = request.form.get("username")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE users SET banned=1 WHERE username=?", (username,))

    conn.commit()
    conn.close()

    return "<script>window.location='/admin'</script>"


# =========================
# UNBAN USER (FIXED FOR HTML FORM)
# =========================
@app.route("/admin/unban", methods=["POST"])
def unban_user():
    username = request.form.get("username")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE users SET banned=0 WHERE username=?", (username,))

    conn.commit()
    conn.close()

    return "<script>window.location='/admin'</script>"


# =========================
# RUN SERVER (RENDER SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
