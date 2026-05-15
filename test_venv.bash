#!/bin/bash

VENV_DIR="./venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment directory not found."
    exit 1
fi

# Check activation script
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Invalid virtual environment: activate script missing."
    exit 1
fi

# Check Python executable
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Invalid virtual environment: python executable missing."
    exit 1
fi

# Test Python execution
"$VENV_DIR/bin/python" --version > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Virtual environment is corrupted or unusable."
    exit 1
fi

echo "Virtual environment is valid and stable."