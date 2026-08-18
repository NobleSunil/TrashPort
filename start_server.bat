@echo off
title TrashPort - Starting Server
color 0A

echo =========================================
echo      TrashPort Dev Server Launcher
echo =========================================
echo.

:: Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [!] No .venv found. Make sure dependencies are installed.
    pause
    exit /b
)
echo.

:: Set environment variables
set DATABASE_URL=sqlite:///db.sqlite3
set DJANGO_READ_DOT_ENV_FILE=True
set DJANGO_DEBUG=True
set DJANGO_SETTINGS_MODULE=config.settings.local

echo [*] Running database migrations...
python manage.py migrate
echo.

echo [*] Starting Django development server...
echo.
echo =========================================
echo   Server running at: http://127.0.0.1:8000
echo   Dashboard URL:     http://127.0.0.1:8000/dashboard/
echo   Press CTRL+C to stop
echo =========================================
echo.

python manage.py runserver 8000

pause
