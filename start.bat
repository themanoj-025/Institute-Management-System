@echo off
setlocal EnableDelayedExpansion

title Binary Brain IMS Launcher
color 0A

echo.
echo ==========================================================
echo       Binary Brain Institute Management System
echo ==========================================================
echo.

:: Move to project directory
cd /d "%~dp0"

:: ----------------------------------------------------------
:: Check Python
:: ----------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo.
    echo Install Python from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

:: ----------------------------------------------------------
:: Create Virtual Environment if Missing
:: ----------------------------------------------------------
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: ----------------------------------------------------------
:: Activate Virtual Environment
:: ----------------------------------------------------------
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b
)

echo.

:: ----------------------------------------------------------
:: Upgrade pip
:: ----------------------------------------------------------
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo.

:: ----------------------------------------------------------
:: Create .env if missing
:: ----------------------------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env file from .env.example...
        copy .env.example .env >nul
    ) else (
        echo [WARNING] .env.example not found. Skipping .env creation.
    )
)

:: ----------------------------------------------------------
:: Install Dependencies
:: ----------------------------------------------------------
if exist "requirements.txt" (
    echo [INFO] Installing dependencies...
    python -m pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found.
)

echo.

:: ----------------------------------------------------------
:: Run Application
:: ----------------------------------------------------------
if exist "main.py" (
    echo [INFO] Launching Binary Brain IMS...
    echo.
    python main.py
) else (
    echo [ERROR] main.py not found.
)

echo.
echo ==========================================================
echo Application Closed
echo ==========================================================
echo.

pause
endlocal