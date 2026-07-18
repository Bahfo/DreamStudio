@echo off
setlocal enabledelayedexpansion

set "VENV_DIR=venv"

:: Check if the virtual environment directory exists
if exist "%VENV_DIR%\" (
    echo [STATUS] Virtual environment found.
) else (
    echo [STATUS] Creating virtual environment...
    python -m venv %VENV_DIR%
    
    :: Check if the previous command failed (equivalent to set -e)
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Make sure Python is installed.
        exit /b 1
    )
    echo [STATUS] Virtual environment created successfully.
)

echo [INFO] Activating virtual environment...
:: Windows equivalent of sleep 2
timeout /t 2 >nul

:: Windows venv uses 'Scripts' instead of 'bin'
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" startup.py
) else (
    echo [ERROR] Python executable not found in virtual environment.
    exit /b 1
)

:: Clearing cached files by calling the companion batch script
if exist "clear_cache.bat" (
    call clear_cache.bat
) else (
    echo [WARNING] clear_cache.bat not found. Skipping cache clear.
)

endlocal