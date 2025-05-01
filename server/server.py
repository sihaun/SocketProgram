import socket
import json
import os
import sys
import time
import threading
from datetime import datetime

USER_DB = "users.json"
LOG_FILE = "server_log.txt"

class Server(socket.socket):
    def __init__(self, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.bind(("", port))
        self.listen(3)

        self.lock_user_db = threading.Lock() # 데이터베이스 중복 접근 방지

        self.default_key = "0" # register시 주어지는 기본 키

    def __exit__(self, exc_type, exc_value, traceback): # 서버 종료
        if exc_type:
            self.log_message(f"An exception occurred: {exc_value}")
        self.log_message("Server closed")
        self.close()

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
    
    def client_handler(self, client_socket : socket.socket, addr) -> None:
        '''
        연결된 client의 data 수신 => request를 보고 response 생성 후 전송
        response를 
        
        client_socket : socket.socket. 통신 소켓
        addr : address'''
        self.log_message(f"[{addr[0]}] is accept.")
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
                self.log_message(f"[{addr[0]}] 연결이 강제 종료되었습니다.")
                break

        self.log_message(f"[{addr[0]}] 연결 종료.")
        client_socket.close()

    def request_handler(self, request : str) -> tuple:
        '''
        client로부터 받은 request정보를 처리하는 함수
        
        request를 method, path, headers, body로 나눔.
        method와 path를 보고 처리해야할 함수(handler)에 body data를 보냄.
        
        request : client로부터 받은 request
        
        return : handler의 return 값. client에 다시 보낼 response.
                response에 byte data가 없을 시 (response, None)
                response에 byte data가 존재하면 (response, byte data) 형식
                
                일치하는 path가 없으면 404 return'''
        self.log_message(request)
        lines = request.split("\r\n")
        method, path, _ = lines[0].split(" ")
        headers = lines[1:]
        body = lines[-1]

        if path == "/register" and method == "POST": # register
            '''
            client로부터 입력받은 body의 username, password를 register_handler로 전달'''
            data = json.loads(body)
            return self.register_handler(data["username"], data["password"])
        
        elif path == "/login" and method == "POST": # login
            '''
            client로부터 입력받은 body의 username, password를 login_handler로 전달'''
            data = json.loads(body)
            return self.login_handler(data["username"], data["password"])
        
        elif path == "/privilege" and method == "PUT": # privilege
            '''
            client로부터 입력받은 body의 username을 id로 받아 권한 유효성 검사를 실행.
            이후 결과와 id를 privilege_handler로 전달'''
            data = json.loads(body)
            id = data["username"]
            valid = self._is_valid_key(id)
            return self.privilege_handler(id, valid)
        
        elif path == "/images": # image
            if method == "HEAD":
                '''
                client로부터 입력받은 body의 username을 id로 받아 권한 유효성 검사를 실행.
                유효하다면 200, 유효하지 않다면 401 return'''
                data = json.loads(body)
                id = data["username"]
                if not id:
                    return self._create_response_str("400 Bad Request", body="Missing username")
                
                valid = self._is_valid_key(id) 
                if valid: # check
                    return self._create_response_str("200 OK", body="Valid key")
                else:
                    return self._create_response_str("401 Unauthorized", body="Invalid Key")
            
            elif method == "GET":
                '''
                client로부터 입력받은 body의 image_url을 받아 image_downloader로 전달'''
                url_data = json.loads(body)
                url = url_data["url"]
                return self.image_downloader(url)
        
        return self._create_response_str("404 Not Found", body="Page not found")
    
    def register_handler(self, id : str, password : str) -> tuple:
        '''
        client가 /register로 접근했을 때 처리하는 함수.

        user.json에서 user database를 받아옴 -> 입력받은 id가 존재하는 지 확인.
        존재하지 않으면 id, pw 쌍으로 계정 생성하고 계정 정보를 user database에 저장.
        
        id : client id. 등록하고자 하는 id
        password : client password. 등록하고자 하는 pw
        
        return : tuple(response, None). register_handler는  byte data를 생성하지 않으므로 None.'''
        users = self.load_users()
        if id in users: # 이미 user가 있을 때
            return self._create_response_str("400 Bad Request", body="REGISTER_FAILED: User already exists")
        
        users[id] = {"pw" : password, "key" : {"value" : self.default_key, "expiry_time" : 0} }
        self.save_users(users)
        return self._create_response_str("200 OK", body="REGISTER_SUCCESS") # 등록 완료

    def login_handler(self, id : str, password : str) -> tuple:
        '''
        client가 /login로 접근했을 때 처리하는 함수.

        users.json에서 user database를 받아옴 -> 입력받은 id와 pw 쌍이 존재하는 지 확인
        
        id : login id. 로그인하고자 하는 id
        password : login password. 로그인하고자 하는 pw
        
        return : tuple(response, None). login_handler는  byte data를 생성하지 않으므로 None.'''
        users = self.load_users()
        try:
            if users.get(id)["pw"] == password: # login success
                return self._create_response_str("200 OK", body="LOGIN_SUCCESS")
        except: # get(id) == None or get(id) != password
            '''
            보안을 위해 login success 제외 모든 경우를 401로 return'''
            pass
        return self._create_response_str("401 Unauthorized", body="LOGIN_FAILED")
    
    def privilege_handler(self, id : dict, key_is_valid : bool=True) -> tuple:
        '''
        client가 /privilege로 접근했을 때 처리하는 함수.

        키가 유효하다면 이미 권한이 상승된 상태이므로 409 도출.
        키가 유효하지 않다면 권한이 상승되지 않았거나 키의 유효기간이 만료된 상태이므로 키를 새로 발급해줌.
        
        id : login id. 권한을 상승하고자 하는 id
        key_is_vaild : client key의 유효 여부
        
        return : tuple(response, None). login_handler는  byte data를 생성하지 않으므로 None.'''
        users = self.load_users()  

        if key_is_valid: # 이전에 키가 발급되었음
            return self._create_response_str("409 Conflict", body="PRIVILEGE_ALREADY_CHANGED")
        
        # 키 발급
        users.get(id)["key"]["value"] = "ABCD"
        users.get(id)["key"]["expiry_time"] = time.time() + 3600 # 유효시간 : 1시간
        self.save_users(users)

        headers = [f"Set-Cookie: key=ABCD; Max-Age=3600"]
        return self._create_response_str("200 OK", headers, body="PRIVILEGE_CHANGED")
    
    def image_downloader(self, url : str) -> tuple:
        '''
        client가 /images로 접근했을 때 처리하는 함수

        client가 요청한 이미지 url이 존재하면 이미지를 byte data로 전달 
        존재하지 않으면 404 도출

        url : client가 요청한 image file

        return : image가 존재하면 response와 byte data를 튜플로 전달.
                 image가 존재하지 않으면 response와 None을 전달.
        '''
        if os.path.exists(url):
            with open(url, "rb") as f:
                image_data = f.read()
            return self._create_response_byte("200 OK", headers=["Content-Type: image/jpg", "Content-Disposition: attachment",f"filename={url}"], body=image_data)
        return self._create_response_str("404 Not Found", body="Image not found")

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
    
    def _is_valid_key(self, id : str) -> bool:
        '''
        client id의 key가 유효한 지 검사하는 함수
        
        users.json에서 id를 보고 user key 정보를 받아옴

        False :
        key["value"] == self.default_key => 권한 상승하지 않음
        time.time() > key["expiry_time"] => key의 유효 기간이 지남

        id : user id

        return : bool
        '''
        users = self.load_users()
        key = users.get(id)["key"]

        if key["value"] == self.default_key or time.time() > key["expiry_time"]: # Invalid
            return False
        
        return True
    
    def log_message(self, message):
        '''
        서버가 생성한 메세지들을 LOG_FILE에 저장.

        timestamp message 형태로 저장
        
        message : 서버가 생성한 메세지'''
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} {message}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(message)


def main(port):
    '''
    Start Server
    
    서버를 열고 client를 기다림.
    클라이언트가 접근 => client_handler 실행
    을 무한 반복'''
    with Server(port) as server:
        try:
            while True:
                client_socket, addr = server.accept()
                server.client_handler(client_socket, addr)
        except KeyboardInterrupt:
            print("서버 종료 중...")


if __name__ == "__main__":
    '''
    argv[1] : port
    threading을 통해 client마다 socket을 새로 생성'''
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    threading_socket = threading.Thread(target=main, args=(port,)) # threading socket
    print(f"Server started at {port}")
    threading_socket.start()
