#!/bin/bash

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

source venv/bin/activate

# Run the application
python3 src/main.py
