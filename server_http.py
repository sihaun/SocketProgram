import socket
import sys
import csv
import os
from datetime import datetime

MAX_ACCOUNTS = 50
ACCOUNTS_FILE = "accounts.csv"
LOG_FILE = "server_log.txt"

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

def save_to_csv(accounts, filename):
    with open(filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(accounts)

def load_from_csv(filename):
    accounts = []
    if os.path.exists(filename):
        with open(filename, mode="r", newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            accounts = [row for row in reader if len(row) == 2]
    return accounts

def log_message(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")
    print(message)

def is_valid_id(user_id):
    return user_id.isalnum() and len(user_id) <= 12

def is_valid_pw(pw):
    has_upper = any(ch.isupper() for ch in pw)
    has_digit = any(ch.isdigit() for ch in pw)
    has_special = any(ch in "!@#$" for ch in pw)
    return has_upper and has_digit and has_special and len(pw) >= 8

def is_duplicate_id(accounts, user_id):
    return any(acc[0] == user_id for acc in accounts)

def handle_register(clnt_sock, accounts):
    # 아이디 요청
    clnt_sock.sendall("아이디를 입력하세요:\n".encode("utf-8"))
    user_id = clnt_sock.recv(1024).decode("utf-8").strip()

    if is_duplicate_id(accounts, user_id):
        clnt_sock.sendall("이미 존재하는 ID입니다.\n".encode("utf-8"))
        return

    if not is_valid_id(user_id):
        clnt_sock.sendall("유효하지 않은 ID입니다.\n".encode("utf-8"))
        return

    # 비밀번호 요청
    clnt_sock.sendall("비밀번호를 입력하세요:\n".encode("utf-8"))
    pw = clnt_sock.recv(1024).decode("utf-8").strip()

    if not is_valid_pw(pw):
        clnt_sock.sendall("유효하지 않은 PW입니다.\n".encode("utf-8"))
        return

    # 회원가입 성공
    accounts.append([user_id, pw])
    clnt_sock.sendall("회원가입 성공\n".encode("utf-8"))

def handle_login(clnt_sock, accounts):
    # 아이디 요청
    clnt_sock.sendall("아이디를 입력하세요:\n".encode("utf-8"))
    user_id = clnt_sock.recv(1024).decode("utf-8").strip()

    # 비밀번호 요청
    clnt_sock.sendall("비밀번호를 입력하세요:\n".encode("utf-8"))
    pw = clnt_sock.recv(1024).decode("utf-8").strip()

    for acc in accounts:
        if acc[0] == user_id and acc[1] == pw:
            clnt_sock.sendall("로그인 성공\n".encode("utf-8"))
            return

    clnt_sock.sendall("로그인 실패\n".encode("utf-8"))

def handle_client(clnt_sock, accounts):
    try:
        while True:
            # 서비스 선택 요청
            clnt_sock.sendall(
                "사용할 서비스를 선택하세요:\n1. 회원가입\n2. 로그인\n99. 종료\n".encode("utf-8")
            )
            user_input = clnt_sock.recv(1024).decode("utf-8").strip()

            if user_input == "1":
                handle_register(clnt_sock, accounts)
            elif user_input == "2":
                handle_login(clnt_sock, accounts)
            elif user_input == "99":
                clnt_sock.sendall("종료합니다.\n".encode("utf-8"))
                break
            else:
                clnt_sock.sendall("잘못된 입력입니다. 다시 시도하세요.\n".encode("utf-8"))
    except Exception as e:
        log_message(f"클라이언트 처리 중 예외 발생: {e}")
    finally:
        clnt_sock.close()

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    accounts = load_from_csv(ACCOUNTS_FILE)

    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv_sock.bind(("", port))
    serv_sock.listen(5)
    log_message(f"서버가 포트 {port}에서 시작되었습니다.")

    try:
        while True:
            clnt_sock, addr = serv_sock.accept()
            log_message(f"[{addr[0]}]가 접속하였습니다.")
            handle_client(clnt_sock, accounts)
    except KeyboardInterrupt:
        log_message("서버가 종료됩니다.")
    finally:
        save_to_csv(accounts, ACCOUNTS_FILE)
        serv_sock.close()

if __name__ == "__main__":
    main()