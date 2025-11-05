@echo off
chcp 65001 > nul
title Telegram Signal Bot v13.3
color 0A
echo.
echo ========================================
echo   텔레그램 신호봇 v13.3 시작
echo ========================================
echo.
echo 텔레그램 앱에서 시작 메시지 확인!
echo Ctrl+C로 중지 가능
echo.

python telegram_signal_bot.py

pause
