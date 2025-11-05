@echo off
chcp 65001 >nul
echo ============================================
echo    .env 파일 설정 도우미
echo ============================================
echo.

REM TOKEN 입력
set /p TOKEN="텔레그램 BOT TOKEN 입력: "
set /p CHAT_ID="텔레그램 CHAT_ID 입력: "

echo.
echo [1/3] 스캘핑 봇 .env 생성 중...
copy config_scalp.txt .env.scalp >nul
powershell -Command "(Get-Content .env.scalp) -replace 'PUT_YOUR_TELEGRAM_BOT_TOKEN', '%TOKEN%' | Set-Content .env.scalp"
powershell -Command "(Get-Content .env.scalp) -replace 'PUT_YOUR_CHAT_ID', '%CHAT_ID%' | Set-Content .env.scalp"
echo ✓ .env.scalp 생성 완료

echo [2/3] 단타 봇 .env 생성 중...
copy config_intraday.txt .env.intraday >nul
powershell -Command "(Get-Content .env.intraday) -replace 'PUT_YOUR_TELEGRAM_BOT_TOKEN', '%TOKEN%' | Set-Content .env.intraday"
powershell -Command "(Get-Content .env.intraday) -replace 'PUT_YOUR_CHAT_ID', '%CHAT_ID%' | Set-Content .env.intraday"
echo ✓ .env.intraday 생성 완료

echo [3/3] 스윙 봇 .env 생성 중...
copy config_swing.txt .env.swing >nul
powershell -Command "(Get-Content .env.swing) -replace 'PUT_YOUR_TELEGRAM_BOT_TOKEN', '%TOKEN%' | Set-Content .env.swing"
powershell -Command "(Get-Content .env.swing) -replace 'PUT_YOUR_CHAT_ID', '%CHAT_ID%' | Set-Content .env.swing"
echo ✓ .env.swing 생성 완료

echo.
echo ============================================
echo    .env 파일 설정 완료!
echo ============================================
echo.
echo 다음 명령으로 봇을 시작하세요:
echo     start_3bots.bat
echo.
echo 또는:
echo     docker-compose up -d
echo.
pause
