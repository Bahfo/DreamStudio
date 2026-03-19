#!/bin/bash
TARGET_DIR="${1:-.}"

find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} +
