@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env. Please fill LLM_API_KEY ^(starts with sk-^).
    notepad ".env"
    pause
    exit /b
)

findstr /b /c:"LLM_API_KEY=sk-" ".env" >nul
if errorlevel 1 (
    echo Please fill LLM_API_KEY ^(starts with sk-^) in .env, save, then double-click again.
    notepad ".env"
    pause
    exit /b
)

title Customer Service Agent - CLI
venv\Scripts\python.exe main.py --interactive
echo.
pause
