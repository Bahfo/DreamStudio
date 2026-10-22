#!/usr/bin/env bash

set -e

readonly YELLOW='\033[0;33m'
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

readonly ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_DIR="${ROOT_DIR}/venv"
readonly PYTHON="${VENV_DIR}/bin/python"

clear 2>/dev/null || true

printf "${YELLOW}"
cat <<'LOGO'
 ____                           ____  _             _ _       
|  _ \ _ __ ___  __ _ _ __ ___ / ___|| |_ _   _  __| (_) ___  
| | | | '__/ _ \/ _` | '_ ` _ \\___ \| __| | | |/ _` | |/ _ \ 
| |_| | | |  __/ (_| | | | | | |___) | |_| |_| | (_| | | (_) |
|____/|_|  \___|\__,_|_| |_| |_|____/ \__|\__,_|\__,_|_|\___/ 

LOGO
printf "${NC}"

echo "DreamStudio | EXcellent TechStack"
echo "Copyright (C) 2026 - All Rights Reserved."
echo "Visit us at: https://homepage.xtechstax.duckdns.org/"
printf "%b\n" "${RED}DreamStudio is licensed under the GPLv3 License.${NC}"
printf "\n"

sleep 4

echo -e "${GREEN}[INFO]${NC} Starting DreamStudio..."

if [[ ! -f "${ROOT_DIR}/startup.py" ]]; then
    echo -e "${RED}[ERROR]${NC} startup.py not found."
    exit 1
fi

if [[ -x "$PYTHON" ]]; then
    echo -e "${YELLOW}[STATUS]${NC} Virtual environment found."
else
    echo -e "${YELLOW}[STATUS]${NC} Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}[SUCCESS]${NC} Virtual environment created."
fi

echo -e "${GREEN}[INFO]${NC} Launching DreamStudio..."
"$PYTHON" "${ROOT_DIR}/startup.py"

find "$ROOT_DIR" \
    -path "$VENV_DIR" -prune -o \
    -type d -name "__pycache__" -prune -exec rm -rf {} +

echo -e "${GREEN}[SUCCESS]${NC} DreamStudio closed successfully."
