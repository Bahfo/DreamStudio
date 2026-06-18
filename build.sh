#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Excellent TechStacks - 2026${NC}"
sleep 3
echo -e "${GREEN}DreamStudio IDE Solution Builder${NC}"
sleep 2
echo -e "${NC}Please wait while master builder configures requirements...${NC}"
sleep 2

VENV_DIR="venv"

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


REQUIREMENTS="requirements.txt"

if [ -f "$REQUIREMENTS" ]; then
    echo -e "${GREEN}[INFO] Found $REQUIREMENTS. Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r $REQUIREMENTS
    echo -e "${YELLOW}[STATUS] All dependencies installed.${NC}"
else
    echo -e "${RED}[ERROR] $REQUIREMENTS not found! Cannot proceed with installation.${NC}"
    exit 1
fi


REQUIRED_ASSETS=("assets/" "assets/logo.png") 
ASSETS_MISSING=0

echo -e "${GREEN}[INFO] Verifying project assets...${NC}"
for asset in "${REQUIRED_ASSETS[@]}"; do
    if [ -e "$asset" ]; then
        echo -e "  - $asset: ${GREEN}AVAILABLE${NC}"
    else
        echo -e "  - $asset: ${RED}MISSING${NC}"
        ASSETS_MISSING=$((ASSETS_MISSING + 1))
    fi
done

if [ $ASSETS_MISSING -gt 0 ]; then
    echo -e "${RED}[ERROR] $ASSETS_MISSING required asset(s) are missing. Fix them before building.${NC}"
    exit 1
else
    echo -e "${GREEN}[SUCCESS] All assets verified.${NC}"
fi
