import socket
import json
import sys
import time

SERVER_IP = "000.000.0.0"
DNS = {
    "server": SERVER_IP,
    }

class Client(socket.socket):
    def __init__(self, host : str, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.host = self.domain_to_ip(host)
        self.port = port
        self.session_cookie = {"key" : {"value" : None, "expiry_time" : 0},
                               "key1" : {"value" : 1, "expiry_time" : 0}}
        self.is_logined = False
        self.id = None

        try:
            self.connect((self.host, self.port))
        except Exception as e:
            print("connect() error:", e)
            sys.exit(1)
    
    def __exit__(self):
        print("Client closed")
        self.close()

    def _create_request(self, method, url, body, headers=None):
        """ HTTP 응답을 생성하는 함수 """
        response = [f"{method} {url} HTTP/1.1"]
        response.append(f"Host: {self.host}")

        cookies = []
        for cookie in list(self.session_cookie.keys()):
            if time.time() < self.session_cookie[cookie]["expiry_time"]: # 기간 안지났으면
                cookies.append(f"{cookie}={self.session_cookie[cookie]["value"]}") # 쿠키 추가
            else :
                del self.session_cookie[cookie]
        cookies = "; ".join(cookies)
        if cookies:
            headers_cookie = "Set-Cookie: " + cookies
            response.append(headers_cookie)

        if headers:
            response.extend(headers)
        
        response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
        response.append("")  # 헤더 종료
        response.append(body)  # 본문 추가
        return "\r\n".join(response)

    def _send_request(self, request : str) -> str:
        try:
            self.sendall(request.encode())
        except Exception as e:
            print("write() error:", e)

    def _response_handler(self):
        try:
            _response = self.recv(1024).decode()
        except Exception as e:
            print("read() error:", e)

        # Set-Cookie 처리 (쿠키 저장)
        if "Set-Cookie" in _response:
            for line in _response.split("\r\n"):
                if line.startswith("Set-Cookie:"):
                    name, max_age = line.split(": ")[1].split("; ")
                    self.session_cookie[name.split("=")[0]] = {"value" : name.split("=")[1], "expiry_time" : time.time() + int(max_age.split("=")[1])}
                    
        return _response
    
    def _is_domain(self, host : str) -> bool:
        try:
            domain = host.split(".")
            if domain[0].isnumeric():
                return False
            elif domain[0] == "www" and domain[1].isalpha():
                return True
            else:
                print(f"Invalid domain/ip: {host}")
                sys.exit(1)
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    def domain_to_ip(self, host : str) -> str:
        if self._is_domain(host):
            domain = host.split(".")[1]
            try:
                return DNS[domain]
            except Exception as e:
                print(f"Domain not found: {domain}")
                sys.exit(1)
        else:
            return host

    # 회원가입 요청
    def register(self, username : str, password : str):
        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/register", data, headers="Content-Type: application/json")
        self._send_request(request)
        response = self._response_handler()
        print(response)

        if "REGISTER_SUCCESS" in response:
            print(f"회원가입 성공: {username}")
        elif "User already exists" in response:
            print(f"이미 가입한 유저가 존재합니다. 다른 id를 사용해주세요: {username}")

    # 로그인 요청 (쿠키 저장됨)
    def login(self, username : str, password : str):
        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/login", data, headers="Content-Type: application/json")
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

    def upgrade_privilege(self):
        data = json.dumps({"username": self.id})
        request = self._create_request("PUT", "/privilege", data, headers="Content-Type: application/json")
        self._send_request(request)
        response = self._response_handler()
        print(response)

        # 타임스탬프를 로컬 시간으로 변환
        local_time = time.localtime(self.session_cookie["key"]["expiry_time"])
        # 로컬 시간을 문자열로 출력
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        if "PRIVILEGE_CHANGED" in response:
            print(f"권한 부여됨 expiry_time : {formatted_time}")
        elif "PRIVILEGE_ALREADY_CHANGED" in response:
            print(f"이미 권한이 부여되었습니다 expiry_time : {formatted_time}")

    # 쿠키 확인 요청
    def check_cookie(self):
        pass

def main(host : str, port : int):
    client = Client(host, port)

    while True:
        print("사용할 서비스를 선택하세요:")
        print("1. 회원가입 (POST /register)")
        print("2. 로그인 (POST /login)")
        if client.is_logined:
            print("3. 권한 상승 요청 (PUT /)")
            print("5. 이미지 보기 (GET /)")
            print("6. 파일 다운로드 (GET /)")
        print("99. 종료")
        user_input = input("> ")
        
        if user_input == "1":
            # 회원가입 요청
            user_id = input("아이디를 입력하세요: ")
            password = input("비밀번호를 입력하세요: ")
            client.register(user_id, password)

        elif user_input == "2":
            # 로그인 요청
            user_id = input("아이디를 입력하세요: ")
            password = input("비밀번호를 입력하세요: ")
            client.login(user_id, password)

        elif client.is_logined and user_input == "3":
            # 권한 상승 요청 
            client.upgrade_privilege()

        elif client.is_logined and user_input == "4":
            # 
            pass

        elif client.is_logined and user_input == "5":
            # 이미지 보기
            pass

        elif client.is_logined and user_input == "6":
            # 파일 다운로드
            pass

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
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])

    main(server_host, server_port)
