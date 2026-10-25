@echo off
echo === Backend: creating virtual environment and installing packages ===
cd /d "%~dp0backend"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
echo.
echo === Frontend: installing npm packages ===
cd /d "%~dp0frontend"
call npm install
echo.
echo Setup finished. Now run run-backend.bat and run-frontend.bat in two terminals.
pause
