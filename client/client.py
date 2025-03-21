import socket
import json
import argparse
import sys

SERVER_IP = "000.000.0.0"
DNS = {
    "server": SERVER_IP,
    }

class Client(socket.socket):
    def __init__(self, host : str, port : int):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.host = self.domain_to_ip(host)
        self.port = port
        self.session_cookie = None

    def _send_request(self, request : str) -> str:

        self.sendall(request.encode())
        _response = self.recv(1024).decode()

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
        request = f"POST /register HTTP/1.1\r\nHost: {self.host}\r\nContent-Length: {len(data)}\r\n\r\n{data}"
        print(self._send_request(request))

    # 로그인 요청 (쿠키 저장됨)
    def login(self, username : str, password : str):
        data = json.dumps({"username": username, "password": password})
        request = f"POST /login HTTP/1.1\r\nHost: {self.host}\r\nContent-Length: {len(data)}\r\n\r\n{data}"
        print(self._send_request(request))
        print(f"Saved Cookie: {self.session_cookie}")

    # 쿠키 확인 요청
    def check_cookie(self):
        if self.session_cookie:
            request = f"GET /check_cookie HTTP/1.1\r\nHost: {self.host}\r\nCookie: {self.session_cookie}\r\n\r\n"
        else:
            request = f"GET /check_cookie HTTP/1.1\r\nHost: {self.host}\r\n\r\n"

        print(self._send_request(request))

def main(host : str, port : int):
    client = Client(host, port)

    try:
        client.connect((host, port))
    except Exception as e:
        print("connect() error:", e)
        sys.exit(1)

    while True:

        user_input = input("사용할 서비스를 선택하세요:")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-h", help="Server host", type=str)
    parser.add_argument("--port", "-p", help="Server port", type=int, default=8080)
    args = parser.parse_args()

    main(args.host, args.port)
