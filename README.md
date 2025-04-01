# SocketProgram

# HTTP Server

이것은 `socket` 모듈을 사용하여 Python으로 구현된 간단한 HTTP 서버입니다. 사용자 등록, 로그인, 권한 상승, 이미지 다운로드 기능을 제공합니다.

## 기능
- JSON 데이터베이스(`users.json`)를 사용한 사용자 등록 및 인증
- 키 기반 인증을 통한 권한 상승
- 이미지 파일 검색 및 다운로드
- 멀티스레드 클라이언트 처리

## 요구 사항
- Python 3.x

## 설치
이 저장소를 클론하고 프로젝트 디렉토리로 이동하세요:

```sh
$ git clone https://github.com/sihaun/SocketProgram.git
$ cd SocketProgram
```

## 사용법
포트 번호를 지정하여 서버를 실행하세요:

```sh
$ python server.py <port>
```

예시:

```sh
$ python server.py 8080
```

이렇게 하면 서버가 `8080` 포트에서 시작되며, 클라이언트의 요청을 대기합니다.

## API 엔드포인트
### 1. 사용자 등록
**엔드포인트:** `POST /register`

**요청:**
```json
{
  "username": "사용자명",
  "password": "비밀번호"
}
```

**응답:**
- `200 OK`: 등록 성공
- `400 Bad Request`: 사용자 이미 존재함

### 2. 사용자 로그인
**엔드포인트:** `POST /login`

**요청:**
```json
{
  "username": "사용자명",
  "password": "비밀번호"
}
```

**응답:**
- `200 OK`: 로그인 성공
- `401 Unauthorized`: 잘못된 자격 증명

### 3. 권한 상승
**엔드포인트:** `POST /privilege`

**요청:**
```json
{
  "username": "사용자명"
}
```

**응답:**
- `200 OK`: 권한 상승 완료, 키 발급됨
- `409 Conflict`: 이미 권한 상승됨

### 4. 이미지 다운로드
**엔드포인트:** `POST /images`

**요청:**
```json
{
  "url": "이미지_파일_경로"
}
```

**응답:**
- `200 OK`: 바이너리 파일로 이미지 반환
- `404 Not Found`: 이미지 파일 없음

### 5. 이미지 키 유효성 검사
**엔드포인트:** `HEAD /images`

**요청:**
```json
{
  "username": "사용자명"
}
```

**응답:**
- `200 OK`: 키가 유효함
- `401 Unauthorized`: 키가 유효하지 않거나 만료됨

## 서버 설계
- 서버는 지정된 포트에서 요청을 대기하며, 클라이언트의 연결을 수락합니다.
- 각 클라이언트 요청은 별도의 스레드에서 처리되어 다중 접속을 지원합니다.
- 사용자 인증 데이터는 `users.json` 파일에 저장됩니다.
- 권한 상승은 1시간 동안 유효한 액세스 키를 사용하여 처리됩니다.
- 적절한 키가 제공되면 서버에서 이미지 파일을 제공합니다.

## 주의 사항
- `users.json` 파일이 존재하지 않는 경우, 서버가 요청을 처리할 때 자동으로 빈 JSON 파일을 생성합니다.
- 보안 강화를 위해 이 구현에는 암호화가 포함되어 있지 않습니다. 실제 운영 환경에서는 HTTPS를 사용하는 것이 좋습니다.

-----------------

# HTTP Client

이 프로젝트는 Python의 `socket` 모듈을 사용하여 서버와 통신하는 간단한 HTTP 클라이언트입니다.  
회원가입, 로그인, 권한 상승, 이미지 조회 등의 기능을 제공합니다.

## 기능

- 서버와의 HTTP 요청/응답 처리
- 회원가입 및 로그인
- 로그인 후 권한 상승 요청 가능
- 권한 상승 후 이미지 조회 가능
- 쿠키를 이용한 인증 유지

## 요구 사항

- Python 3.x
- `pillow` 라이브러리 (이미지 처리용)

설치는 다음과 같이 진행합니다.

```sh
$ pip install pillow
```

## 사용법

클라이언트를 실행하려면 서버의 IP와 포트를 지정하여 실행합니다.

```sh
$ python client.py <server_ip> <port>
```

예제:

```sh
$ python client.py 127.0.0.1 8080
```

## API 사용 방법

### 1. 회원가입 (POST /register)
- 사용자가 회원가입할 수 있습니다.

**요청 데이터:**  
```json
{
  "username": "사용자명",
  "password": "비밀번호"
}
```

**응답:**  
- `REGISTER_SUCCESS` : 회원가입 성공  
- `User already exists` : 이미 존재하는 사용자  

### 2. 로그인 (POST /login)
- 로그인하면 쿠키가 저장됩니다.

**요청 데이터:**  
```json
{
  "username": "사용자명",
  "password": "비밀번호"
}
```

**응답:**  
- `LOGIN_SUCCESS` : 로그인 성공  
- `LOGIN_FAILED` : 로그인 실패  

### 3. 권한 상승 (PUT /privilege)
- 로그인 후 권한을 상승시킬 수 있습니다.

**요청 데이터:**  
```json
{
  "username": "사용자명"
}
```

**응답:**  
- `PRIVILEGE_CHANGED` : 권한 상승 완료  
- `PRIVILEGE_ALREADY_CHANGED` : 이미 권한이 상승됨  

### 4. 이미지 조회 (GET /images)
- 권한 상승 후 서버에서 이미지를 받아올 수 있습니다.

**요청 데이터:**  
```json
{
  "url": "이미지_파일_경로"
}
```

**응답:**  
- `200 OK` : 이미지 반환  
- `404 Not Found` : 이미지 없음  

## 주의 사항

- `cookies.json` 파일이 클라이언트 인증을 위해 사용됩니다.
- `web_cash` 폴더에 다운로드된 이미지가 저장됩니다.
- 도메인 사용 시 `SERVER_IP` 값을 사전에 설정해야 합니다.

-------------------------------------------------------------------
SocketProgramming With Python

처음에 접속해서 파일 다운로드 요청 -> 그거 다운받아서 회원가입, 로그인

처음에 회원가입, 로그인 -> 파일 다운로드 권한 요청(권한 상승) -> 유저 key를 쿠키에 저장 -> 키가 맞으면 다운로드
                    or 이미지 보여주기 요청 -> 이미지는 웹 캐시에 저장

register(POST) : -> register_handler
    id : 중복 안됨. 
    pw : 나중에 조건 추가 고려
    id : { "pw" : password, "key" : key}

login(POST) : -> login_handler
    is_logined = True

privilege_handler
권한 상승 요청(PUT). 로그인 되어있어야 함. 상승할 수 있는 권한이어야 함. -> key 발급, 쿠키에 저장.

image_handler
이미지 보여주기 요청(GET). 로그인 되어있어야 함. -> 이미지는 웹 캐시에 저장.
-> 권한 HEAD로 보고 권한 적합하면 다운로드

file_handler
파일 다운로드 요청(GET). 로그인 되어있어야 함. key가 맞아야 함.
-> 권한 HEAD로 보고 권한 적합하면 다운로드