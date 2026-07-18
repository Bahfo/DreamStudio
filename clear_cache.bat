@echo off
set "TARGET_DIR=."

echo Cleaning up __pycache__ directories...

:: Loops through all directories named __pycache__ and deletes them quietly
for /f "delims=" %%i in ('dir /b /s /ad "%TARGET_DIR%\__pycache__" 2^>nul') do (
    rd /s /q "%%i"
)

echo __pycache__ directories removed.