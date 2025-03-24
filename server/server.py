import socket
import json
import os
import sys
import time
import threading

USER_DB = "users.json"
SESSION_DB = {}  # 쿠키 저장용

class Server(socket.socket):
    def __init__(self, port):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.bind(("", port))
        self.listen(3)
        print(f"Server started at {port}")

        self.lock_user_db = threading.Lock()

        self.default_key = "0"

    def __exit__(self):
        print("Server closed")
        self.close()

    def load_users(self):
        with self.lock_user_db:
            if not os.path.exists(USER_DB):
                return {} # 나중에 파일이 없을 때 파일 추가
            with open(USER_DB, "r") as file:
                return json.load(file)

    def save_users(self, users):
        with self.lock_user_db:
            with open(USER_DB, "w") as file:
                json.dump(users, file, indent=4)

    def client_handler(self, client_socket : socket.socket, addr):
        print(f"[{addr[0]}] is accept.")
        while True:
            try:
                request = client_socket.recv(1024).decode()  # 클라이언트로부터 데이터 수신
                if not request:
                    break  # 클라이언트가 연결을 종료하면 루프 종료

                response = self.request_handler(request)
                client_socket.sendall(response.encode())

            except ConnectionResetError:
                print(f"[{addr[0]}] 연결이 강제 종료되었습니다.")
                break

        print(f"[{addr[0]}] 연결 종료.")
        client_socket.close()

    def _create_response(self, status, body=None, headers=None):
        """ HTTP 응답을 생성하는 함수 """
        response = [f"HTTP/1.1 {status}"]
        if headers:
            response.extend(headers)
        if body:
            response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
            response.append("")  # 헤더 종료
            response.append(body)  # 본문 추가
        return "\r\n".join(response)

    def register_handler(self, id, password):
        users = self.load_users()
        if id in users:
            return self._create_response("400 Bad Request", "REGISTER_FAILED: User already exists")
        
        users[id] = {"pw" : password, "key" : {"value" : self.default_key, "expiry_time" : 0} }
        self.save_users(users)
        return self._create_response("200 OK", "REGISTER_SUCCESS")

    def login_handler(self, id, password):
        users = self.load_users()
        if users.get(id)["pw"] == password:
            session_id = f"{id}"
            SESSION_DB[session_id] = id  # 세션 저장

            headers = [f"Set-Cookie: session_id={session_id}; Max-Age=3600"]
            return self._create_response("200 OK", "LOGIN_SUCCESS", headers)

        return self._create_response("401 Unauthorized", "LOGIN_FAILED")
    
    def privilege_handler(self, valid=True, check=True):
        users = self.load_users()  

        if check:
            if valid:
                return self._create_response("200 OK")
            return self._create_response("401 Unauthorized")
        
        if valid:
            return self._create_response("409 Conflict", "PRIVILEGE_ALREADY_CHANGED")
        
        users.get(id)["key"]["value"] = "ABCD"
        users.get(id)["key"]["expiry_time"] = time.time() + 3600
        self.save_users(users)

        headers = [f"Set-Cookie: key=ABCD; Max-Age=3600"]
        return self._create_response("200 OK", "PRIVILEGE_CHANGED", headers)

    def request_handler(self, request):
        print(request)
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
        
        elif path == "/privilege": # privilege
            data = json.loads(body)
            id = data["username"]
            is_valid = self._is_valid_key(id)

            return self.privilege_handler(is_valid) if method == "HEAD" else self.privilege_handler(is_valid, check=False)
        
        elif path == "/image": # image
            if method == "HEAD": # 이미지 존재 요청
                pass
                    # 이미지 보여주기 요청

        elif path == "/file": # file
            if method == "HEAD": # 파일 존재 요청
                pass
                    # 파일 다운로드 요청
        
        return self._create_response("404 Not Found", "Page not found")
    
    def _is_valid_key(self, id):
        users = self.load_users()
        key = users.get(id)["key"]

        if key["value"] == self.default_key or time.time() > key["expiry_time"]: # Invalid
            return False
        
        return True

def main(port):
    server = Server(port)

    while True:
        client_socket, addr = server.accept()
        threading_client_handler = threading.Thread(target=server.client_handler, args=(client_socket, addr))
        threading_client_handler.start()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    main(port)
