@echo off
chcp 65001 > nul
rem 둘 AI 서버 + 시연판 실행 (Windows). 처음 한 번은 .env.example 을 .env 로 복사해서 키를 채우세요.
cd /d "%~dp0"
if not exist .env (copy .env.example .env > nul & echo .env 파일을 만들었어요. 키를 채운 뒤 다시 실행하세요. & notepad .env & exit /b 1)
python -m pip install -q -r requirements.txt
cd ..\src
python build_app.py
cd ..\server
echo.
echo 브라우저에서 http://localhost:8000 을 여세요. (가상 회원 user001~user500 / 비밀번호 1234)
python -m uvicorn main:app --port 8000
