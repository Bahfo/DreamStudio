@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Excellent TechStacks - 2026
echo ========================================
echo DreamStudio IDE Solution Builder
echo ========================================
echo Please wait while master builder configures requirements...
echo.

set VENV_DIR=venv

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [STATUS] Virtual environment found.
) else (
    echo [STATUS] Creating virtual environment...
    python -m venv %VENV_DIR%
    echo [STATUS] Virtual environment created successfully.
)

echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

set REQUIREMENTS=requirements.txt

if exist "%REQUIREMENTS%" (
    echo [INFO] Found %REQUIREMENTS%. Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r %REQUIREMENTS%
    echo [STATUS] All dependencies installed.
) else (
    echo [ERROR] %REQUIREMENTS% not found! Cannot proceed with installation.
    exit /b 1
)

echo [INFO] Verifying project assets...
set ASSETS_MISSING=0

if exist "assets\" (
    echo   - assets/: AVAILABLE
) else (
    echo   - assets/: MISSING
    set /a ASSETS_MISSING+=1
)
if exist "assets\logo.png" (
    echo   - assets/logo.png: AVAILABLE
) else (
    echo   - assets/logo.png: MISSING
    set /a ASSETS_MISSING+=1
)

if %ASSETS_MISSING% gtr 0 (
    echo [ERROR] %ASSETS_MISSING% required asset(s) are missing. Fix them before building.
    exit /b 1
) else (
    echo [SUCCESS] All assets verified.
)
