@echo off
echo ===================================================
echo Binary Brain IMS - Windows Quick Installer
echo ===================================================

echo [1/3] Creating virtual environment...
python -m venv venv

echo [2/3] Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo [3/3] Setting up environment variables...
if not exist .env (
    copy .env.example .env
    echo Created .env file from .env.example.
) else (
    echo .env file already exists.
)

echo.
echo ===================================================
echo Installation Complete!
echo You can now run the app with:
echo venv\Scripts\activate
echo python main.py
echo ===================================================
pause
