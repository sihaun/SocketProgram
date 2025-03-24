import socket
import json
import os
import sys
import time
import threading

USER_DB = "users.json"
SESSION_DB = {}  # 쿠키 저장용

class Server(socket.socket):
    def __init__(self, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.bind(("", port))
        self.listen(3)
        print(f"Server started at {port}")

        self.lock_user_db = threading.Lock()

        self.default_key = "0"

    def __exit__(self):
        print("Server closed")
        self.close()

    def load_users(self) -> dict:
        with self.lock_user_db:
            if not os.path.exists(USER_DB):
                return {} # 나중에 파일이 없을 때 파일 추가
            with open(USER_DB, "r") as file:
                return json.load(file)

    def save_users(self, users : dict) -> None:
        with self.lock_user_db:
            with open(USER_DB, "w") as file:
                json.dump(users, file, indent=4)

    def client_handler(self, client_socket : socket.socket, addr) -> None:
        print(f"[{addr[0]}] is accept.")
        while True:
            try:
                request = client_socket.recv(1024).decode()  # 클라이언트로부터 데이터 수신
                if not request:
                    break  # 클라이언트가 연결을 종료하면 루프 종료

                response, bin_file = self.request_handler(request)
                if bin_file:
                    client_socket.sendall(response.encode() + bin_file)
                else: 
                    client_socket.sendall(response.encode())

            except ConnectionResetError:
                print(f"[{addr[0]}] 연결이 강제 종료되었습니다.")
                break

        print(f"[{addr[0]}] 연결 종료.")
        client_socket.close()

    def _create_response(self, status : str, headers : list=None, body=None) -> str:
        """ HTTP 응답을 생성하는 함수 """
        response = [f"HTTP/1.1 {status}"]
        if headers:
            response.extend(headers)
        if body:
            response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
            response.append("")  # 헤더 종료
            response.append(body)  # 본문 추가
        return "\r\n".join(response)

    def register_handler(self, id : str, password : str) -> str:
        users = self.load_users()
        if id in users:
            return self._create_response("400 Bad Request", body="REGISTER_FAILED: User already exists")
        
        users[id] = {"pw" : password, "key" : {"value" : self.default_key, "expiry_time" : 0} }
        self.save_users(users)
        return self._create_response("200 OK", body="REGISTER_SUCCESS")

    def login_handler(self, id : str, password : str) -> str:
        users = self.load_users()
        if users.get(id)["pw"] == password:
            session_id = f"{id}"
            SESSION_DB[session_id] = id  # 세션 저장

            headers = [f"Set-Cookie: session_id={session_id}; Max-Age=3600"]
            return self._create_response("200 OK", headers, body="LOGIN_SUCCESS")

        return self._create_response("401 Unauthorized", body="LOGIN_FAILED")
    
    def privilege_handler(self, key_is_valid : bool=True, check : bool=True) -> None:
        users = self.load_users()  

        if check:
            if key_is_valid:
                return self._create_response("200 OK")
            return self._create_response("401 Unauthorized")
        
        if key_is_valid:
            return self._create_response("409 Conflict", body="PRIVILEGE_ALREADY_CHANGED")
        
        users.get(id)["key"]["value"] = "ABCD"
        users.get(id)["key"]["expiry_time"] = time.time() + 3600
        self.save_users(users)

        headers = [f"Set-Cookie: key=ABCD; Max-Age=3600"]
        return self._create_response("200 OK", headers, body="PRIVILEGE_CHANGED")
    
    def image_downloader(self, url : str) -> str:
        if os.path.exists(url):
            with open(url, "rb") as f:
                image_data = f.read()
            return self._create_response("200 OK", headers=[f"Content-Type: image/jpeg", "Content-Disposition: attachment", "filename={url}"]), image_data
        
        return self._create_response("404 Not Found", "Image not found")


    def request_handler(self, request : str) -> tuple:
        print(request)
        lines = request.split("\r\n")
        method, path, _ = lines[0].split(" ")
        headers = lines[1:]
        body = lines[-1]

        if method == "POST" and path == "/register": # register
            data = json.loads(body)
            return self.register_handler(data["username"], data["password"]), None
        
        elif method == "POST" and path == "/login": # login
            data = json.loads(body)
            return self.login_handler(data["username"], data["password"]), None
        
        elif path == "/privilege": # privilege
            data = json.loads(body)
            id = data["username"]
            valid = self._is_valid_key(id)

            return self.privilege_handler(valid), None if method == "HEAD" else self.privilege_handler(valid, check=False), None
        
        elif path == "/image": # image
            if method == "HEAD":
                data = json.loads(body)
                id = data["username"]
                valid = self._is_valid_key(id)
                return self._create_response("200 OK"), None if valid else self._create_response("401 Unauthorized"), None # check key
            
            return self.image_downloader(body)
            if os.path.exists(IMAGE_PATH):
                with open(IMAGE_PATH, "rb") as f:
                    image_data = f.read()

            retur

        elif method == "HEAD" and path == "/file": # file
            if method == "HEAD": # 파일 존재 요청
                pass
                    # 파일 다운로드 요청
        
        return self._create_response("404 Not Found", "Page not found"), None
    
    def _is_valid_key(self, id : str) -> bool:
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
