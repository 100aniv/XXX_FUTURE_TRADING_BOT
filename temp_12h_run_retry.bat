@echo off
cd /d C:\Users\bback\OneDrive\Documents\future_alarm_bot
call trading_bot_env\Scripts\activate.bat
python scripts\run_paper.py --config configs\scalping\real_paper_12h_v6_1_phase17.yml
