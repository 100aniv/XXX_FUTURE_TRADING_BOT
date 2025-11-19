@echo off
cd /d C:\Users\bback\OneDrive\Documents\future_alarm_bot
call trading_bot_env\Scripts\activate.bat
echo [Monitor] Starting 12H monitoring at %date% %time%
python scripts\monitor_12h_acceptance.py
echo [Monitor] Ended at %date% %time%
pause
