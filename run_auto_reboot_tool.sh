#!/bin/bash
# Intersect Engine Auto Reboot Tool Launcher (Linux/Mac)

cd "$(dirname "$0")"

python3 auto_reboot_tool.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Error: Failed to start auto reboot tool"
    echo "Make sure Python 3 is installed and accessible"
    exit 1
fi


