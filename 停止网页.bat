@echo off
chcp 65001 >nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*streamlit_app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Web server stopped.
timeout /t 2 >nul
