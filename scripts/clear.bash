#!/bin/bash
TARGET_DIR="/home/bahaa/Desktop/apps/DreamStudio-IDE"

find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} +
