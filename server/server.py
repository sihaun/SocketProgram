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

        self.lock_user_db = threading.Lock() # 데이터베이스 중복 접근 방지지

        self.default_key = "0" # register시 주어지는 기본 키

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            print(f"An exception occurred: {exc_value}")
        print("Server closed")
        self.close()

    def load_users(self) -> dict:
        '''
        유저 데이터베이스에 있는 내용을 load함'''
        with self.lock_user_db:
            if not os.path.exists(USER_DB):
                return {} 
            with open(USER_DB, "r") as file:
                return json.load(file)

    def save_users(self, users : dict) -> None:
        '''
        user에 있는 내용을 유저 데이터베이스에 업데이트
        
        users : dict'''
        with self.lock_user_db:
            with open(USER_DB, "w") as file:
                json.dump(users, file, indent=4)

    def client_handler(self, client_socket : socket.socket, addr) -> None:
        '''
        연결된 client의 data 수신 => request를 보고 response 생성 후 전송
        response를 
        
        client_socket : socket.socket. 통신 소켓
        addr : address'''
        print(f"[{addr[0]}] is accept.")
        while True:
            try:
                request = client_socket.recv(4096).decode()  # 클라이언트로부터 데이터 수신
                if not request:
                    break  # 클라이언트가 연결을 종료하면 루프 종료

                (response, bin_file) = self.request_handler(request)
                if bin_file is not None: # 
                    client_socket.sendall(response.encode() + bin_file)
                else: 
                    client_socket.sendall(response.encode())

            except ConnectionResetError:
                print(f"[{addr[0]}] 연결이 강제 종료되었습니다.")
                break

        print(f"[{addr[0]}] 연결 종료.")
        client_socket.close()

    def _create_response_str(self, status : str, headers : list=None, body : str=None) -> tuple:
        """ HTTP 응답을 생성하는 함수 
        
        status : 응답 상태
        headers : 헤더들을 리스트로 전달
        body : string data
        
        return : response를 string으로 전달, None(byte 데이터가 존재하지 않음)"""
        response = [f"HTTP/1.1 {status}"]
        if headers:
            response.extend(headers)
        if body:
            response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
            response.append("")  # 헤더 종료
            response.append(body)  # 본문 추가
        return ("\r\n".join(response), None)
    
    def _create_response_byte(self, status : str, headers : list, body : bytes) -> tuple:
        """ HTTP 응답을 생성하는 함수 

        status : 응답 상태
        headers : 헤더들을 리스트로 전달
        body : data를 byte형식으로 전달

        return : response를 string으로 전달, byte data"""
        response = [f"HTTP/1.1 {status}"]
        response.extend(headers)

        response.append(f"Content-Length: {len(body)}")  # 본문 길이 추가
        response.append("\r\n")  # 헤더 종료

        return ("\r\n".join(response), body)

    def register_handler(self, id : str, password : str) -> tuple:
        users = self.load_users()
        if id in users:
            return self._create_response_str("400 Bad Request", body="REGISTER_FAILED: User already exists")
        
        users[id] = {"pw" : password, "key" : {"value" : self.default_key, "expiry_time" : 0} }
        self.save_users(users)
        return self._create_response_str("200 OK", body="REGISTER_SUCCESS")

    def login_handler(self, id : str, password : str) -> tuple:
        users = self.load_users()
        try:
            if users.get(id)["pw"] == password:
                session_id = f"{id}"
                SESSION_DB[session_id] = id  # 세션 저장

                headers = [f"Set-Cookie: session_id={session_id}; Max-Age=3600"]
                return self._create_response_str("200 OK", headers, body="LOGIN_SUCCESS")
        except:
            pass
        return self._create_response_str("401 Unauthorized", body="LOGIN_FAILED")
    
    def privilege_handler(self, id : dict, key_is_valid : bool=True, check : bool=True) -> tuple:
        users = self.load_users()  

        if check:
            if key_is_valid:
                return self._create_response_str("200 OK")
            return self._create_response_str("401 Unauthorized")
        
        if key_is_valid:
            return self._create_response_str("409 Conflict", body="PRIVILEGE_ALREADY_CHANGED")
        
        users.get(id)["key"]["value"] = "ABCD"
        users.get(id)["key"]["expiry_time"] = time.time() + 3600
        self.save_users(users)

        headers = [f"Set-Cookie: key=ABCD; Max-Age=3600"]
        return self._create_response_str("200 OK", headers, body="PRIVILEGE_CHANGED")
    
    def image_downloader(self, url : str) -> str:
        if os.path.exists(url):
            with open(url, "rb") as f:
                image_data = f.read()
            return self._create_response_byte("200 OK", headers=["Content-Type: image/jpg", "Content-Disposition: attachment",f"filename={url}"], body=image_data)
        return self._create_response_str("404 Not Found", body="Image not found")

    def request_handler(self, request : str) -> tuple:
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
            valid = self._is_valid_key(id)

            return self.privilege_handler(id, valid, check=False)
        
        elif path == "/images": # image
            if method == "HEAD":
                data = json.loads(body)
                id = data["username"]
                valid = self._is_valid_key(id)
                return self._create_response_str("200 OK") if valid else self._create_response_str("401 Unauthorized") # check key
            
            url_data = json.loads(body)
            url = url_data["url"]
            return self.image_downloader(url)

        elif method == "HEAD" and path == "/file": # file
            if method == "HEAD": # 파일 존재 요청
                pass
                    # 파일 다운로드 요청
        
        return self._create_response_str("404 Not Found", body="Page not found")
    
    def _is_valid_key(self, id : str) -> bool:
        users = self.load_users()
        key = users.get(id)["key"]

        if key["value"] == self.default_key or time.time() > key["expiry_time"]: # Invalid
            return False
        
        return True

def main(port):
    with Server(port) as server:
        while True:
            client_socket, addr = server.accept()
            server.client_handler(client_socket, addr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    threading_socket = threading.Thread(target=main, args=port) # threading socket
    print(f"Server started at {port}")
    threading_socket.start()
