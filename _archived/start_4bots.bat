@echo off
chcp 65001 >nul
echo ============================================
echo    4개 봇 동시 실행 스크립트
echo    (TREND + REVERSION + BREAKOUT + ENSEMBLE)
echo ============================================
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았습니다!
    pause
    exit /b 1
)

echo [1/4] TREND 봇 시작...
start "TREND Bot" cmd /k "python signal_bot_trend.py"
timeout /t 2 /nobreak >nul

echo [2/4] REVERSION 봇 시작...
start "REVERSION Bot" cmd /k "python signal_bot_reversion.py"
timeout /t 2 /nobreak >nul

echo [3/4] BREAKOUT 봇 시작...
start "BREAKOUT Bot" cmd /k "python signal_bot_breakout.py"
timeout /t 2 /nobreak >nul

echo [4/4] ENSEMBLE 봇 시작...
start "ENSEMBLE Bot" cmd /k "python ensemble_bot.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo    ✅ 4개 봇이 모두 시작되었습니다!
echo ============================================
echo.
echo 각 봇은 별도 창에서 실행 중입니다.
echo 종료하려면 각 창에서 Ctrl+C를 누르세요.
echo.
pause
