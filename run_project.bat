@echo off
title Log File Anomaly Explainer Launcher
echo =======================================================
echo     LogSentry AI - Anomaly Explainer Web Launcher
echo =======================================================
echo.

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found on your system PATH.
        echo Please download and install Python from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

:: Create Virtual Environment if it doesn't exist
if not exist venv (
    echo [*] Creating virtual environment (venv)...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Trying backup command...
        py -m venv venv
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to set up venv. Running locally without venv...
            set USE_VENV=0
        ) else (
            set USE_VENV=1
        )
    ) else (
        set USE_VENV=1
    )
) else (
    set USE_VENV=1
)

:: Activate Virtual Environment
if "%USE_VENV%"=="1" (
    echo [*] Activating virtual environment...
    call .\venv\Scripts\activate.bat
)

:: Install Dependencies
echo [*] Checking and installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Dependency installation encountered issues. Trying alternatives...
    python -m pip install -r requirements.txt
)

:: Open Browser automatically in 2 seconds in a separate process
echo [*] Starting web browser...
start "" http://127.0.0.1:5000

:: Run the Flask Application
echo.
echo =======================================================
echo  Flask Server is running!
echo  Open http://127.0.0.1:5000 in your browser if it didn't open.
echo  To shut down the server, press CTRL+C in this window.
echo =======================================================
echo.
python app.py

pause
