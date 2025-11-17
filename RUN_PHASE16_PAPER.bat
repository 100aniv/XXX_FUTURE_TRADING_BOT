@echo off
REM ==========================================================
REM PHASE16 REAL Paper Mode - 12시간 실행 스크립트
REM ==========================================================
REM 
REM 사전 조건:
REM   - Docker Redis/PostgreSQL 실행 중
REM   - 가상환경 활성화
REM   - 네트워크 안정
REM
REM ==========================================================

echo ================================================================================
echo 🚀 PHASE16 REAL Paper Mode - 12시간 실행
echo ================================================================================
echo.

REM 1. 가상환경 활성화
echo [1/4] 가상환경 활성화...
call .\trading_bot_env\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패
    pause
    exit /b 1
)
echo ✅ 가상환경 활성화 완료
echo.

REM 2. Redis 확인
echo [2/4] Redis 연결 확인...
docker exec trading_redis redis-cli ping > nul 2>&1
if errorlevel 1 (
    echo ❌ Redis 연결 실패 - Docker 컨테이너 확인 필요
    pause
    exit /b 1
)
echo ✅ Redis PONG 확인
echo.

REM 3. 사전 상태 확인
echo [3/4] 현재 상태 확인...
python scripts/check_paper.py
echo.

REM 4. Paper Trading 시작
echo [4/4] Paper Trading 시작...
echo ================================================================================
echo 전략: scalping
echo 심볼: BTCUSDT
echo 타임프레임: 3m
echo Duration: 12 hours
echo ================================================================================
echo.
echo ⚠️  실행 후 다른 터미널에서 모니터링:
echo    python scripts/monitor_paper.py
echo.
echo ⚠️  12시간 후 리포트 생성:
echo    python scripts/generate_report_phase16.py --latest
echo.
echo ================================================================================
echo 🟢 Paper Trading 시작 (Ctrl+C로 중단)
echo ================================================================================
echo.

python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --timeframe 3m --duration-hours 12

echo.
echo ================================================================================
echo ✅ Paper Trading 종료
echo ================================================================================
pause
