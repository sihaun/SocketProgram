import socket
import json
import sys
import time
import os

SERVER_IP = "000.000.0.0"
COOKIES_DB = "cookies.json"
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
        self.id = None

        try:
            self.connect((self.host, self.port))
        except Exception as e:
            print("connect() error:", e)
            sys.exit(1)

        self.load_cookies()

    def load_cookies(self) -> None:
        try:
            with open(COOKIES_DB, "r") as file:
                self.session_cookie = json.load(file)
        except:
            self.session_cookie = {}

    def save_cookies(self, cookies : dict) -> None:
            with open(COOKIES_DB, "w") as file:
                json.dump(cookies, file, indent=4)
    
    def __exit__(self):
        self.save_cookies(self.session_cookie)
        print("Client closed")
        self.close()

    def _create_request(self, method : str, url : str, headers : list=None, body : str=None) -> str:
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

        if body:
            response.append(f"Content-Length: {len(body.encode())}")  # 본문 길이 추가
            response.append("")  # 헤더 종료

            response.append(body)  # 본문 추가

        return "\r\n".join(response)

    def _send_request(self, request : str) -> str:
        try:
            self.sendall(request.encode())
        except Exception as e:
            print("write() error:", e)

    def _response_handler(self, bin_data=False) -> str:
        _response = ""
        try:
            if not bin_data:
                _response = self.recv(4096).decode()
                print(f"_response : \n{_response}")
            else:
                _b_response = self.recv(4096)
                (header, image_data) = _b_response.split(b"\r\n\r\n", 1)
                print("header.decode() :", header.decode())

                return (header.decode(), image_data)

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
    def register(self, username : str, password : str) -> None:
        data = json.dumps({"username": username, "password": password})
        request = self._create_request("POST", "/register", headers=["Content-Type: application/json"], body=data)
        self._send_request(request)
        response = self._response_handler()
        print(response)

        if "REGISTER_SUCCESS" in response:
            print(f"회원가입 성공: {username}")
        elif "User already exists" in response:
            print(f"이미 가입한 유저가 존재합니다. 다른 id를 사용해주세요: {username}")

    # 로그인 요청 (쿠키 저장됨)
    def login(self, username : str, password : str) -> None:
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

    def download_image(self, url : str) -> None:
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
        request = self._create_request("GET", "/images", headers=["Content-Type: application/json"], body=url_data)
        self._send_request(request)
        (headers, image_data) = self._response_handler(bin_data=True)
        headers = headers.decode()
        print("headers :\n", headers)

        if "200 OK" in headers:
            with open(url, "wb") as f:
                f.write(image_data)
                print(f"[+] 이미지 저장 완료: {url}")

        elif "Image not found" in headers:
            print(f"이미지가 존재하지 않습니다. Image : {url}")




def main(host : str, port : int):
    client = Client(host, port)

    while True:
        print("사용할 서비스를 선택하세요:")
        if not client.is_logined:
            print("1. 회원가입 (POST /register)")
            print("2. 로그인 (POST /login)")
        else:
            print("3. 권한 상승 요청 (PUT /)")
            print("4. 이미지 다운로드 (GET /)")
            print("5. 파일 다운로드 (GET /)")
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
            url = input("다운받을 이미지 이름을 입력하세요: ")
            client.download_image(url)

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
