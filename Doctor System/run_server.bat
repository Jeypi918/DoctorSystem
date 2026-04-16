@echo off
cd /d "%~dp0"
echo Starting Django Development Server...
echo.
echo Server will run at: http://127.0.0.1:8000/
echo Login page: http://127.0.0.1:8000/login/
echo.
echo Press Ctrl+C to stop the server
echo.
"C:\Users\CHMC User\AppData\Local\Python\pythoncore-3.14-64\python.exe" manage.py runserver 0.0.0.0:8000
pause
