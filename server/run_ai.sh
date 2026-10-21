#!/usr/bin/env bash
# 둘 AI 서버 + 시연판 실행 (Mac / Linux). 처음 한 번은 .env.example 을 .env 로 복사해서 키를 채우세요.
set -e
cd "$(dirname "$0")"
[ -f .env ] || { cp .env.example .env; echo ".env 파일을 만들었어요. 키를 채운 뒤 다시 실행하세요."; exit 1; }
python3 -m pip install -q -r requirements.txt
(cd ../src && python3 build_app.py)
echo "브라우저에서 http://localhost:8000 을 여세요. (가상 회원 user001~user500 / 비밀번호 1234)"
python3 -m uvicorn main:app --port 8000
