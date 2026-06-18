@echo off
setlocal

echo ========================================
echo Excellent TechStacks - 2026
echo ========================================
echo DreamStudio IDE Tools Pipeline
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

echo [INFO] Installing development tools...
pip install ruff pytest pytest-qt

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

echo.
echo ========================================
echo Running lint checks...
echo ========================================
ruff check .

echo.
echo ========================================
echo Running formatter...
echo ========================================
ruff format .

echo.
echo ========================================
echo Running tests...
echo ========================================
pytest -v
