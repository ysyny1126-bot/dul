@echo off
chcp 65001 > nul
rem 둘: 기존 데이터를 모두 지우고 새로 배포 (Windows)
cd /d "%~dp0"
echo 기존 데이터(회원 프로필, 좋아요, 채팅, 사진, 마음 표현)를 모두 지우고 새로 배포해요.
set /p ans=계속할까요? (y/N)
if /i not "%ans%"=="y" (echo 취소했어요. & exit /b 1)
echo [1/2] 기존 데이터 지우는 중...
call firebase firestore:delete --all-collections --force
echo [2/2] 사이트와 보안 규칙 배포 중...
call firebase deploy
echo 끝! 위에 나온 Hosting URL로 들어가 보세요.
pause
