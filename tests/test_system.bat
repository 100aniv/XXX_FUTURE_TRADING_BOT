@echo off
REM 시스템 통합 테스트 스크립트
REM 각 단계별로 동작 확인

echo ========================================
echo 시스템 통합 테스트
echo ========================================
echo.

REM 1. Conda 환경 활성화
echo [1/6] Conda 환경 활성화...
call conda activate trading_bot
if errorlevel 1 (
    echo ❌ Conda 환경 활성화 실패
    echo    먼저 setup_conda_env.bat을 실행하세요
    pause
    exit /b 1
)
echo ✅ Conda 환경 활성화 성공
echo.

REM 2. .env 파일 확인
echo [2/6] 환경 변수 파일 확인...
if not exist .env (
    echo ❌ .env 파일이 없습니다
    echo    env.example을 복사해서 .env를 만드세요:
    echo    copy env.example .env
    pause
    exit /b 1
)
echo ✅ .env 파일 존재
echo.

REM 3. PostgreSQL 확인
echo [3/6] PostgreSQL 연결 확인...
docker ps | findstr postgres >nul
if errorlevel 1 (
    echo ❌ PostgreSQL 컨테이너가 실행 중이 아닙니다
    echo    다음 명령어로 시작하세요:
    echo    docker-compose up -d postgres
    pause
    exit /b 1
)
echo ✅ PostgreSQL 실행 중
echo.

REM 4. Python 모듈 import 테스트
echo [4/6] Python 모듈 테스트...
python -c "import psycopg2; import pandas; import numpy; print('✅ 모듈 import 성공')"
if errorlevel 1 (
    echo ❌ 필수 모듈 import 실패
    echo    pip install -r requirements.txt 실행 필요
    pause
    exit /b 1
)
echo.

REM 5. DB 연결 테스트
echo [5/6] DB 연결 테스트...
python -c "import os; os.environ['DATABASE_URL']='postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'; import psycopg2; conn=psycopg2.connect(os.environ['DATABASE_URL']); print('✅ DB 연결 성공')"
if errorlevel 1 (
    echo ❌ DB 연결 실패
    echo    .env 파일의 DATABASE_URL 확인
    pause
    exit /b 1
)
echo.

REM 6. TradingExecutor import 테스트
echo [6/6] TradingExecutor 모듈 테스트...
python -c "from trading_executor import TradingExecutor, PositionTracker, PositionSizer, RiskManager; print('✅ TradingExecutor import 성공')"
if errorlevel 1 (
    echo ❌ TradingExecutor import 실패
    pause
    exit /b 1
)
echo.

echo ========================================
echo ✅ 모든 테스트 통과!
echo ========================================
echo.
echo 다음 단계:
echo 1. 시그널 봇 실행: python telegram_signal_bot.py
echo 2. Trading Manager 실행: python trading_manager.py
echo.
pause
