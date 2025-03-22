# SocketProgram
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
이미지 존재하는지 요청(HEAD)
이미지 보여주기 요청(GET). 로그인 되어있어야 함. -> 이미지는 웹 캐시에 저장.

file_handler
파일 존재하는지 요청(HEAD)
파일 다운로드 요청(GET). 로그인 되어있어야 함. key가 맞아야 함.