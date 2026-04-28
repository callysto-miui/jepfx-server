from flask import Flask, request, jsonify

app = Flask(__name__)

# 📂 DATABASE OF USERS
users = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0"
}

# 🌐 CHECK SERVER STATUS
@app.route('/', methods=['GET'])
def home():
    return "✅ SERVER IS RUNNING!", 200

# 🔐 LOGIN FUNCTION
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if username in users and users[username] == password:
            return jsonify({"success": True, "message": "Login Success"})
        else:
            return jsonify({"success": False, "message": "Wrong Username or Password"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
