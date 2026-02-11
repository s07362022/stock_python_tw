@echo off
chcp 65001 >nul
cd /d "%~dp0"
python daily_us_tw_email.py --send
pause
