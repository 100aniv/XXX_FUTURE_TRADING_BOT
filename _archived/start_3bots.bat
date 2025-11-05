@echo off
echo ============================================
echo    3개 봇 동시 실행 스크립트
echo ============================================
echo.

REM .env 파일 존재 확인
if not exist ".env.scalp" (
    echo [오류] .env.scalp 파일이 없습니다!
    echo config_scalp.txt를 .env.scalp로 복사하고 TOKEN을 설정하세요.
    pause
    exit /b 1
)

if not exist ".env.intraday" (
    echo [오류] .env.intraday 파일이 없습니다!
    echo config_intraday.txt를 .env.intraday로 복사하고 TOKEN을 설정하세요.
    pause
    exit /b 1
)

if not exist ".env.swing" (
    echo [오류] .env.swing 파일이 없습니다!
    echo config_swing.txt를 .env.swing로 복사하고 TOKEN을 설정하세요.
    pause
    exit /b 1
)

echo [1/3] 기존 실행 중인 봇 확인...
docker-compose ps

echo.
echo [2/3] Docker 컨테이너 빌드 및 시작...
docker-compose up -d --build

echo.
echo [3/3] 상태 확인...
timeout /t 3 /nobreak >nul
docker-compose ps

echo.
echo ============================================
echo    3개 봇이 실행되었습니다!
echo ============================================
echo.
echo 로그 확인: docker-compose logs -f
echo 중지: docker-compose down
echo 재시작: docker-compose restart
echo.
pause
