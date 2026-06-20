#!bin/bash
# (C) Copyright 2026 EXcellent TechStacks - All Rights Reserved
# Bootstrapper for DreamStudio Installation Process

set -e 

mkdir -p ~/.dreamstudio && cd ~/.dreamstudio
echo "[DEBUG] Downloading DreamStudio from source ..."

# TODO: Write the installer

# Deletes all files related to windows before initialization
# to ensure that non-related OS files are all removed
remove_windows_related_files() {
    find . type -f -name "*.bat" -delete
}

