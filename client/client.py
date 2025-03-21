import socket
import json
import argparse

PORT = 5000
session_cookie = None  # 쿠키 저장

def send_request(request):
    global session_cookie

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        client.sendall(request.encode())
        response = client.recv(1024).decode()

    # Set-Cookie 처리 (쿠키 저장)
    if "Set-Cookie" in response:
        for line in response.split("\r\n"):
            if line.startswith("Set-Cookie:"):
                session_cookie = line.split(": ")[1]
                break

    return response

# 회원가입 요청
def register(username, password):
    data = json.dumps({"username": username, "password": password})
    request = f"POST /register HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: {len(data)}\r\n\r\n{data}"
    print(send_request(request))

# 로그인 요청 (쿠키 저장됨)
def login(username, password):
    data = json.dumps({"username": username, "password": password})
    request = f"POST /login HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: {len(data)}\r\n\r\n{data}"
    print(send_request(request))
    print(f"Saved Cookie: {session_cookie}")

# 쿠키 확인 요청
def check_cookie():
    if session_cookie:
        request = f"GET /check_cookie HTTP/1.1\r\nHost: {HOST}\r\nCookie: {session_cookie}\r\n\r\n"
    else:
        request = f"GET /check_cookie HTTP/1.1\r\nHost: {HOST}\r\n\r\n"

    print(send_request(request))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="Server host")
    parser.add_argument("--port", help="Server port", type=int, default=PORT)
    args = parser.parse_args()
    # 테스트 실행
    register("user1", "pass123")
    login("user1", "pass123")
    check_cookie()
