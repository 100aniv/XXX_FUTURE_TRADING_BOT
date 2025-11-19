@echo off
cd /d C:\Users\bback\OneDrive\Documents\future_alarm_bot
call trading_bot_env\Scripts\activate.bat
echo [12H Acceptance] Starting at %date% %time%
python scripts\run_paper.py --config configs\scalping\real_paper_12h_v6_1_phase17.yml
echo [12H Acceptance] Ended at %date% %time%
pause
