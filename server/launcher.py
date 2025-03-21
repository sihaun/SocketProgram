import socket
import os

HOST = "0.0.0.0"  
PORT = 8080        
FILENAME = "example.txt"  # 제공할 파일

def handle_client(client_socket):
    """클라이언트 요청을 처리하고 파일을 HTTP 응답으로 전송"""
    request = client_socket.recv(1024).decode()  # HTTP 요청 읽기
    print(f"📩 요청 수신:\n{request}")

    # HTTP 응답 헤더
    if os.path.exists(FILENAME):
        file_size = os.path.getsize(FILENAME)
        header = f"HTTP/1.1 200 OK\r\n"
        header += f"Content-Type: application/octet-stream\r\n"
        header += f"Content-Length: {file_size}\r\n"
        header += f"Content-Disposition: attachment; filename={FILENAME}\r\n"
        header += "\r\n"
        
        client_socket.send(header.encode())  # 응답 헤더 전송

        # 파일 데이터 전송
        with open(FILENAME, "rb") as f:
            while chunk := f.read(1024):
                client_socket.send(chunk)

        print(f"📤 파일 '{FILENAME}' 전송 완료!")
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\nFile Not Found"
        client_socket.send(response.encode())

    client_socket.close()

def start_server():
    """HTTP 서버 시작"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)  # 최대 5개의 클라이언트 대기 가능

    print(f"🚀 서버 시작! http://{HOST}:{PORT} 에서 대기 중...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"✅ 클라이언트 연결됨: {addr}")
        handle_client(client_socket)

if __name__ == "__main__":
    start_server()
