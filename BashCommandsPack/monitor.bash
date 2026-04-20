#!/bin/bash

#  COPYRIGHT 2026 DREAMSTUDIO TEAM - BASH COMMANDS PACK  #

echo "Disk Usage"
read -p "Enter threshold value (e.g., 80): " threshold

# Disk Usage
usage=$(df -h | grep " /$" | awk '{print $5}' | tr -d "%")
if [ "$usage" -gt $threshold ]; then 
    echo "Low disk space: $usage %"
else echo "Disk space usage: $usage %"
fi

# Memory Usage
memory_space=$(free -m | grep "Mem:" | awk '{print int(($3 / $2) * 100)}')
if [ "$memory_space" -gt $threshold ]; then
    echo "Low memory space. Usage: $memory_space %"
else echo "Memory usage: $memory_space %"
fi