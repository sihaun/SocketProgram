import json
import os

USER_DB = "users.json"

def load_users():
    if not os.path.exists(USER_DB):
        return {}
    
    with open(USER_DB, "r") as file:
        return json.load(file)

def save_users(users):
    with open(USER_DB, "w") as file:
        json.dump(users, file, indent=4)

def handle_register(username, password):
    users = load_users()

    if username in users:
        return "REGISTER_FAILED: User already exists"
    
    users[username] = password  # 실제 서비스에서는 비밀번호 해싱 필요
    save_users(users)
    return "REGISTER_SUCCESS"

def handle_login(username, password):
    users = load_users()

    if users.get(username) == password:
        return "LOGIN_SUCCESS"
    return "LOGIN_FAILED"
