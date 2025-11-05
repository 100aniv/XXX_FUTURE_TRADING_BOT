@echo off
REM Conda 가상환경 생성 및 패키지 설치 스크립트
REM 사용법: setup_conda_env.bat

echo ========================================
echo Conda 가상환경 생성 (trading_bot)
echo ========================================

REM 기존 환경이 있으면 삭제
call conda env remove -n trading_bot -y

REM 새 환경 생성 (Python 3.11)
call conda create -n trading_bot python=3.11 -y

REM 환경 활성화
call conda activate trading_bot

echo.
echo ========================================
echo 필수 패키지 설치 중...
echo ========================================

REM 기본 패키지
call pip install python-dotenv==1.0.0
call pip install psycopg2-binary==2.9.9
call pip install requests==2.31.0

REM Binance 관련
call pip install python-binance==1.0.19
call pip install binance-connector==3.7.0

REM 데이터 분석
call pip install pandas==2.1.3
call pip install numpy==1.26.2
call pip install ta==0.11.0

REM 시각화 (백테스트용)
call pip install matplotlib==3.8.2
call pip install seaborn==0.13.0

REM Telegram
call pip install python-telegram-bot==20.7

echo.
echo ========================================
echo 설치 완료!
echo ========================================
echo.
echo 다음 명령어로 환경 활성화:
echo   conda activate trading_bot
echo.
echo 현재 설치된 패키지 확인:
echo   pip list
echo.
pause
