#!/bin/bash

set -e

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

VENV_DIR="venv/"

if [ -d "$VENV_DIR" ]; then 
    echo -e "${YELLOW}[STATUS] Virtual environment found.${NC}"
else
    echo -e "${YELLOW}[STATUS] Creating virtual environment...${NC}"
    python3 -m venv $VENV_DIR
    echo -e "${YELLOW}[STATUS] Virtual environment created successfully.${NC}"
fi

echo -e "${GREEN}[INFO] Activating virtual environment...${NC}"
sleep 2
source $VENV_DIR/bin/activate

# Running
python3 run_test.py

# Clearing cached files
./clear_cache.sh