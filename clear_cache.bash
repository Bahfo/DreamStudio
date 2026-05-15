#!/bin/bash

TARGET_DIR="."

find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} +

echo "__pycache__ directories removed."