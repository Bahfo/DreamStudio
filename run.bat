@echo off
setlocal

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

echo Running DreamStudio...
python run.py

echo Clearing cached files...
for /f "delims=" %%i in ('dir /s /b /ad __pycache__ 2^>nul') do rmdir /s /q "%%i"
