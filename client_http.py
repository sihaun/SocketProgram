import socket
import sys

def build_http_request(method, path, body=""):
    """
    HTTP 요청을 생성하는 함수
    """
    request = f"{method} {path} HTTP/1.1\r\n"
    request += "Host: localhost\r\n"
    request += "Content-Type: application/x-www-form-urlencoded\r\n"
    if body:
        request += f"Content-Length: {len(body)}\r\n"
    request += "\r\n"
    if body:
        request += body
    return request

def main():
    # 명령행 인수가 3개 (프로그램 이름, 서버 IP, 서버 포트)가 아니면 사용법을 출력하고 종료
    if len(sys.argv) != 3:
        print("Usage: {} <IP> <port>".format(sys.argv[0]))
        sys.exit(1)
    
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    
    # TCP 소켓 생성
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 서버에 연결 시도
    try:
        sock.connect((server_ip, server_port))
    except Exception as e:
        print("connect() error:", e)
        sys.exit(1)
    
    while True:
        # 사용자 입력
        print("사용할 서비스를 선택하세요:")
        print("1. 회원가입 (POST /register)")
        print("2. 로그인 (POST /login)")
        print("3. 서버 상태 확인 (GET /)")
        print("99. 종료")
        user_input = input("> ")
        
        if user_input == "1":
            # 회원가입 요청
            user_id = input("아이디를 입력하세요: ")
            password = input("비밀번호를 입력하세요: ")
            body = f"id={user_id}&pw={password}"
            request = build_http_request("POST", "/register", body)
        elif user_input == "2":
            # 로그인 요청
            user_id = input("아이디를 입력하세요: ")
            password = input("비밀번호를 입력하세요: ")
            body = f"id={user_id}&pw={password}"
            request = build_http_request("POST", "/login", body)
        elif user_input == "3":
            # 서버 상태 확인 요청
            request = build_http_request("GET", "/")
        elif user_input == "99":
            print("클라이언트를 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 시도하세요.")
            continue
        
        # 서버로 요청 전송
        try:
            sock.sendall(request.encode())
        except Exception as e:
            print("write() error:", e)
            break
        
        # 서버로부터 응답 수신
        try:
            response = sock.recv(4096).decode()
            print("서버 응답:")
            print(response)
        except Exception as e:
            print("read() error:", e)
            break
    
    # 소켓 닫기
    sock.close()

if __name__ == '__main__':
    main()