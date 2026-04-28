from flask import Flask, request, jsonify

app = Flask(__name__)

# Your allowed users
users = {
    "JEPFX": "@JEPFX_1875",
    "SEAN": "SEAN_0",
    "N4XCO": "N4XCO_0"
}

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = data.get('username')
    pwd = data.get('password')

    if user in users and users[user] == pwd:
        return jsonify({"success": True, "message": "Login OK"})
    else:
        return jsonify({"success": False, "message": "Wrong credentials"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
