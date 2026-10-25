@echo off
cd /d "%~dp0backend"
call .venv\Scripts\activate
echo API: http://localhost:8000   Docs: http://localhost:8000/docs
uvicorn app.main:app --reload --port 8000
