import socket
import json
import sys

SERVER_IP = "000.000.0.7"
DNS = {
    "server": SERVER_IP,
    }

class Client(socket.socket):
    def __init__(self, host : str, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.host = self.domain_to_ip(host)
        self.port = port
        self.session_cookie = None
        self.is_logined = False

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

        try:
            _response = self.recv(1024).decode()
        except Exception as e:
            print("read() error:", e)

        # Set-Cookie 처리 (쿠키 저장)
        if "Set-Cookie" in _response:
            for line in _response.split("\r\n"):
                if line.startswith("Set-Cookie:"):
                    self.session_cookie = line.split(": ")[1]
                    break

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
        response = self._send_request(request)
        print(response)

        if "REGISTER_SUCCESS" in response:
            print(f"회원가입 성공: {username}")
        elif "User already exists" in response:
            print(f"이미 가입한 유저가 존재합니다. 다른 id를 사용해주세요: {username}")

    # 로그인 요청 (쿠키 저장됨)
    def login(self, username : str, password : str):
        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/login", data, headers="Content-Type: application/json")
        response = self._send_request(request)
        print(response)
        print(f"Saved Cookie: {self.session_cookie}")

        if "LOGIN_SUCCESS" in response:
            self.is_logined = True
            print(f"로그인 성공: {username}")
        elif "LOGIN_FAILED" in response:
            print(f"로그인 실패: {username}")

    # 쿠키 확인 요청
    def check_cookie(self):
        if self.session_cookie:
            request = f"GET /check_cookie HTTP/1.1\r\nHost: {self.host}\r\nCookie: {self.session_cookie}\r\n\r\n"
        else:
            request = f"GET /check_cookie HTTP/1.1\r\nHost: {self.host}\r\n\r\n"

        print(self._send_request(request))

def main(host : str, port : int):
    client = Client(host, port)

    while True:
        print("사용할 서비스를 선택하세요:")
        print("1. 회원가입 (POST /register)")
        print("2. 로그인 (POST /login)")
        if client.is_logined:
            print("3. 권한 확인 (GET /)")
            print("4. 권한 상승 요청 (GET /)")
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
            # 권한 확인
            pass

        elif client.is_logined and user_input == "4":
            # 권한 상승 요청
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
