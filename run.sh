#!/bin/bash

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

source venv/bin/activate

# Suppress Qt DBus warnings in dev container environment
export QT_LOGGING_RULES="qt.qpa.theme.gnome=false"
export QT_QPA_PLATFORMTHEME=""

# Run the application
python3 src/main.py
