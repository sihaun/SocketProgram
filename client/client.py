import socket
import json
import sys
import time
from PIL import Image
from io import BytesIO
import os

# client.py 사용 전 지정해줘야 함
SERVER_IP = "127.0.0.1" 
COOKIES_DB = "cookies.json"
DNS = {
    "server": SERVER_IP,
    }

class Client(socket.socket):
    def __init__(self, host : str, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.host = self.domain_to_ip(host)
        self.port = port

        self.session_cookie = {}
        self.is_logined = False
        self.id = None

        # connect client to server
        try:
            self.connect((self.host, self.port))
        except Exception as e:
            print("connect() error:", e)
            sys.exit(1)
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            print(f"An exception occurred: {exc_value}")
        self.save_cookies(self.session_cookie)
        print("Client closed")
        self.close()
        return False  # 예외를 전파하고 싶다면 False를 반환

    def _send_request(self, request : str) -> str:
        '''
        request를 server에 보내는 함수
        
        request : _create_request 로부터 return된 반복 가능한 string'''

        # send request to server
        try:
            self.sendall(request.encode())
        except Exception as e:
            print("write() error:", e)

    def _create_request(self, method : str, url : str, headers : list=None, body : str=None) -> str:
        '''
        creating HTTP request.
        자동으로 self.session_cookie에 있는 쿠키를 붙혀서 request를 만들어 줌.
        쿠키 만료 시간이 지나지 않았을 경우 쿠키를 추가시키고, 시간이 지나면 쿠키 삭제.
        
        method : GET, HEAD, POST, PUT
        url : /register, /login, /privilege, /images
        headers : header 정보가 담긴 list
        body : 내용이 담긴 string data'''

        response = [f"{method} {url} HTTP/1.1"]
        response.append(f"Host: {self.host}")

        cookies = []
        for cookie in list(self.session_cookie.keys()):
            if time.time() < self.session_cookie[cookie]["expiry_time"]: # 기간 안지났으면
                cookies.append(f"{cookie}={self.session_cookie[cookie]["value"]}") # 쿠키 추가
            else :
                del self.session_cookie[cookie] # 기간 지났으면 쿠키 삭제
        cookies = "; ".join(cookies)
        if cookies:
            headers_cookie = "Set-Cookie: " + cookies
            response.append(headers_cookie)

        # add headers
        if headers:
            response.extend(headers)

        if body:
            response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
            response.append("")  # 헤더 종료

            # add body(data)
            response.append(body)

        return "\r\n".join(response)

    def _response_handler(self, bin_data=False):
        '''
        server로부터 받은 response를 header 부분과 data 부분으로 나눔.

        data 부분이 binary 파일인 경우(이미지 파일) header 부분과 binary_data를 return
        data 부분이 string data인 경우 header 부분과 string data를 붙혀서 return
        
        data 부분이 string data인 경우 cookie를 self.session_cookie에 저장
        
        bin_data : True if bin_data is binary else False
        
        return : 
            bin_data = True:
                tuple(header : str, image_data : bytes)
            bin_data = False
                string(_response)'''
        
        # recieve response and data by server
        _response = ""
        if not bin_data:
            _response = self.recv(4096).decode()
            print(f"_response : \n{_response}")
        else: # 여기까지는 들어옴
            _b_response = b""
            while True:
                chunk = self.recv(4 * 1024) # data를 chunk 조각으로 나누어 받음
                if not chunk:
                    break
                
                _b_response += chunk

                # header와 data 분류
                if b"\r\n\r\n" in _b_response: 
                    (header, image_data) = _b_response.split(b"\r\n\r\n", 1)
                    break
            
            while True:
                chunk = self.recv(4096)
                if not chunk:
                    break
                image_data += chunk 
                if len(chunk) < 4096:
                    break

            return (header.decode(), image_data)

        # Set-Cookie 처리 (쿠키 저장)
        if "Set-Cookie" in _response:
            for line in _response.split("\r\n"):
                if line.startswith("Set-Cookie:"):
                    name, max_age = line.split(": ")[1].split("; ")
                    self.session_cookie[name.split("=")[0]] = {"value" : name.split("=")[1], "expiry_time" : time.time() + int(max_age.split("=")[1])}
                    
        return _response

    # 회원가입 요청
    def register(self, username : str, password : str) -> None:
        '''
        회원가입 요청. (POST /register)

        username : string
        password : string

        Body content-Type: json
        '''

        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/register", headers=["Content-Type: application/json"], body=data)
        self._send_request(request)
        response = self._response_handler()
        print(response)

        if "REGISTER_SUCCESS" in response:
            self.load_cookies()
            print(f"회원가입 성공: {username}")
        elif "User already exists" in response:
            print(f"이미 가입한 유저가 존재합니다. 다른 id를 사용해주세요: {username}")

    # 로그인 요청 (쿠키 저장됨)
    def login(self, username : str, password : str) -> None:
        '''
        로그인 요청. (POST /login)

        username : string
        password : string

        Body content-Type: json
        '''

        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/login", headers=["Content-Type: application/json"], body=data)
        self._send_request(request)
        response = self._response_handler()
        print(response)
        print(f"Saved Cookie: {self.session_cookie}")

        if "LOGIN_SUCCESS" in response:
            self.is_logined = True
            self.id = username
            print(f"로그인 성공: {username}")
        elif "LOGIN_FAILED" in response:
            print(f"로그인 실패: {username}")

    def upgrade_privilege(self) -> None:
        '''
        권한 상승(수정) 요청. (PUT /privilege)

        권한 수정 후 sssion_cookie에 key, expiry_time 발급.
        expiry_time 만료 시 재발급 가능.

        Body content-Type: json
        '''

        data = json.dumps({"username": self.id})
        request = self._create_request("PUT", "/privilege", headers=["Content-Type: application/json"], body=data)
        self._send_request(request)
        response = self._response_handler()
        print(response)

        # 타임스탬프를 로컬 시간으로 변환
        local_time = time.localtime(self.session_cookie["key"]["expiry_time"])
        # 로컬 시간을 문자열로 출력
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        if "PRIVILEGE_CHANGED" in response:
            print(f"권한 부여됨 expiry_time : {formatted_time}")
            print(f"Saved Cookie: {self.session_cookie}\n")
        elif "PRIVILEGE_ALREADY_CHANGED" in response:
            print(f"이미 권한이 부여되었습니다 expiry_time : {formatted_time}")

    def show_image(self, url : str) -> None:
        '''
        이미지 보여주기 요청. (HEAD /images) -> (GET /images)

        input을 받아 해당 url의 이미지가 존재하는 지 확인 (HEAD /images)
        이미지가 존재하면, (GET /images)로 이미지 정보를 binary 정보로 가져와 보여줌.

        가져온 이미지는 web_cash에 저장됨.
        url을 확인한 후 먼저 web_cash에 해당 이미지가 존재하는 지 확인한 후 존재하면 가져옴
        존재하지 않으면 (GET /images)를 통해 이미지 정보를 요청.

        url : 원하는 이미지 경로. 확장자를 포함하여야 함. EX) images.jpg

        Body content-Type: json
        '''

        data = json.dumps({"username": self.id})
        check_privilege = self._create_request("HEAD", "/images", headers=["Content-Type: application/json"], body=data)
        self._send_request(check_privilege)
        privilege_response = self._response_handler()
        print(privilege_response)

        if "401 Unauthorized" in privilege_response:
            print("권한이 없습니다. 권한을 상승시켜 주세요.")
            return
        
        # 200 OK
        url_data = json.dumps({"url": url})
        print(f"{url_data}")

        if os.path.exists("web_cash/" + url_data): # web_cash
            image = Image.open("web_cash/" + url_data)
            return
        
        request = self._create_request("GET", "/images", headers=["Content-Type: image/jpg"], body=url_data)
        self._send_request(request)
        (headers, image_data) = self._response_handler(bin_data=True)

        if "200 OK" in headers:
            image = Image.open(BytesIO(image_data))
            image.show()
            image.save("web_cash/downloaded_image.jpg")

        elif "Image not found" in headers:
            print(f"이미지가 존재하지 않습니다. Image : {url}")

    def _is_domain(self, host : str) -> bool:
        '''
        입력된 host가 도메인인 지 확인함.
        
        host : ip address or domain
        
        return : False if host is ip address else host is domain'''

        try:
            domain = host.split(".")
            if domain[0].isnumeric(): # 192.000.0.0
                return False
            elif domain[0] == "www" and domain[1].isalpha(): # www.server.com
                return True
            else:
                print(f"Invalid domain/ip: {host}")
                sys.exit(1)
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    def domain_to_ip(self, host : str) -> str:
        '''
        입력된 host가 domain일 경우 ip address로 변환.
        
        DNS : 
            "domain name" : ip address 형식의 dict
            
        host : ip address or domain
        
        return : ip address'''
        if self._is_domain(host):
            domain = host.split(".")[1]
            try:
                return DNS[domain] # domain name system
            except Exception as e:
                print(f"Domain not found: {domain}")
                sys.exit(1)
        else:
            return host

    def load_cookies(self) -> None:
        '''
        COOKIES_DB에 저장된 client의 쿠키 정보를 loading함.'''
        try:
            with open(COOKIES_DB, "r") as file:
                self.session_cookie = json.load(file)
        except:
            self.session_cookie = {}

    def save_cookies(self, session_cookies : dict) -> None:
        '''
        session_cookies에 저장된 쿠키 내용을 COOKIES_DB에 저장
        
        session_cookies : dict'''
        with open(COOKIES_DB, "w") as file:
            json.dump(session_cookies, file, indent=4)


def main(host : str, port : int):
    '''
    회원가입, 로그인, 권한 상승, 이미지 보기 기능을 이용할 수 있는 클라이언트.
    실행 시 초기 화면으로 회원가입, 로그인 기능만 이용 가능.
    로그인 시 권한 상승, 이미지 보기 기능 이용 가능.
    이미지 보기 기능은 권한이 상승된 상태에서 이용 가능.
    종료는 99를 눌러야 가능.

    회원가입부터 이미지 보기 절차 :
    회원 가입 -> 로그인 -> 권한 상승 요청 -> 이미지 보기

    이전에 회원가입과 로그인까지만 마친 경우 :
    로그인 -> 권한 상승 요청 -> 이미지 보기

    이전에 권한 상승 요청까지 마친 경우 :
    로그인 -> 이미지 보기

    host : domain or ip address.
        domain은 현재 DNS에 www.server 로 지정되어 있음.
        domain을 사용하려면 SERVER_IP에 사전에 server ip address를 입력해 놓아야 함.

        ip address를 입력할 경우 server의 ip address를 str로 입력.

    port : server.py에 사용한 port와 같은 port를 사용
    '''

    with Client(host, port) as client:

        while True:
            print("사용할 서비스를 선택하세요:")
            if not client.is_logined:
                print("1. 회원가입 (POST /register)")
                print("2. 로그인 (POST /login)")
            else:
                print("3. 권한 상승 요청 (PUT /)")
                print("4. 이미지 보기 (GET /)")
            print("99. 종료")
            user_input = input("> ")
            
            if not client.is_logined and user_input == "1":
                # 회원가입 요청
                user_id = input("아이디를 입력하세요: ")
                password = input("비밀번호를 입력하세요: ")
                client.register(user_id, password)

            elif not client.is_logined and user_input == "2":
                # 로그인 요청
                user_id = input("아이디를 입력하세요: ")
                password = input("비밀번호를 입력하세요: ")
                client.login(user_id, password)

            elif client.is_logined and user_input == "3":
                # 권한 상승 요청 
                client.upgrade_privilege()

            elif client.is_logined and user_input == "4":
                url = input("이미지 url을 입력하세요: ")
                client.show_image(url)

            elif user_input == "99":
                print("클라이언트를 종료합니다.")
                break

            else:
                print("잘못된 입력입니다. 다시 시도하세요.")
                continue


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: {} <IP> <port>".format(sys.argv[0]))
        sys.exit(1)
    
    server_host = sys.argv[1] # host
    server_port = int(sys.argv[2]) # port

    main(server_host, server_port)
