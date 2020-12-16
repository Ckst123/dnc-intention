# OPERATOR

## 소개
* 이 설명서는 운영자가 이 프로그램을 운용하기 위한 설명서입니다.

## 사전작업
* Ubuntu 16.04.6 LTS 에서 작동합니다.
* Python 3.5 에서 작동합니다.
* NVIDIA CUDA 8를 지원하는 GPU와 그래픽 드라이버를 필요로 합니다.
* CUDA 8과 cuDNN 5.1 에서 작동합니다.

## 설치
* 상위 경로의 "requirements.txt" 를 python 환경에서 pip로 설치합니다.
* "server.py" 에서 변수 "pkl_data_file", "ckpt_path" 에 옳바른 경로를 지정합니다.
* "server.py" 에서 변수 "port", "server" 의 생성자 변수 "ip" 옳바른 값을 지정합니다.

## 사용법
* python으로 "server.py" 를 실행합니다.
* 정상적으로 실행시, 클라이언트로 오는 한글 문장과 서버에서 분석된 클래스 코드를, 터미널을 통해 확인할 수 있습니다.
* 종료시, "ctrl + c" 를 입력하여 종료합니다.

## 문제해결
* 문제가 발생시 프로그램을 종료하고 다시 실행합니다.
