@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "停止网页.bat"
timeout /t 2 >nul
cscript //nologo "启动网页.vbs"
