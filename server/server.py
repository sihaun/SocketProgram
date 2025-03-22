import socket
import json
import os
import sys

USER_DB = "users.json"
SESSION_DB = {}  # 쿠키 저장용

class Server(socket.socket):
    def __init__(self, port):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.bind(("", port))
        self.listen(3)
        print(f"Server started at {port}")

        self.default_key = "0"

    def __exit__(self):
        print("Server closed")
        self.close()

    def load_users(self):
        if not os.path.exists(USER_DB):
            return {} # 나중에 파일이 없을 때 파일 추가
        with open(USER_DB, "r") as file:
            return json.load(file)

    def save_users(self, users):
        with open(USER_DB, "w") as file:
            json.dump(users, file, indent=4)

    def _create_response(self, status, body, headers=None):
        """ HTTP 응답을 생성하는 함수 """
        response = [f"HTTP/1.1 {status}"]
        if headers:
            response.extend(headers)
        
        response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
        response.append("")  # 헤더 종료
        response.append(body)  # 본문 추가
        return "\r\n".join(response)

    def register_handler(self, id, password):
        users = self.load_users()
        if id in users:
            return self._create_response("400 Bad Request", "REGISTER_FAILED: User already exists")
        
        users[id] = {"pw" : password, "key" : self.default_key}
        self.save_users(users)
        return self._create_response("200 OK", "REGISTER_SUCCESS")

    def login_handler(self, id, password):
        users = self.load_users()
        if users.get(id)["pw"] == password:
            session_id = f"{id}_session"
            SESSION_DB[session_id] = id  # 세션 저장

            headers = [f"Set-Cookie: session_id={session_id}; HttpOnly; Max-Age=3600"]
            return self._create_response("200 OK", "LOGIN_SUCCESS", headers)

        return self._create_response("401 Unauthorized", "LOGIN_FAILED")
    
    def privilege_handler(self):
        pass

    def handle_check_cookie(self, headers):
        cookie_header = next((h for h in headers if h.startswith("Cookie:")), None)
        
        if cookie_header:
            cookies = {}
            for c in cookie_header.replace("Cookie: ", "").split("; "):
                if "=" in c:  # '=' 기호가 있는 경우만 처리
                    key, value = c.split("=", 1)
                    cookies[key] = value
            
            session_id = cookies.get("session_id")
            
            if session_id in SESSION_DB:
                return self._create_response("200 OK", f"Valid session for {SESSION_DB[session_id]}")
        
        return self._create_response("401 Unauthorized", "No valid session")

    def handle_request(self, request):
        lines = request.split("\r\n")
        method, path, _ = lines[0].split(" ")

        headers = lines[1:]
        body = lines[-1]

        if method == "POST" and path == "/register": # register
            data = json.loads(body)
            return self.register_handler(data["username"], data["password"])
        
        elif method == "POST" and path == "/login": # login
            data = json.loads(body)
            return self.login_handler(data["username"], data["password"])
        
        elif method == "GET" and path == "/":
            pass


        elif method == "GET" and path == "/check_cookie": # check_cookie
            return self.handle_check_cookie(headers)
        
        return self._create_response("404 Not Found", "Page not found")

def main(port):
    server = Server(port)

    while True:
        conn, addr = server.accept()
        print((f"[{addr[0]}]is accept."))
        request = conn.recv(1024).decode()

        response = server.handle_request(request)
        conn.sendall(response.encode())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    main(port)
