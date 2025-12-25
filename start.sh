#!/bin/bash

# Ensure script stops on first error
set -e

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found or invalid."
    exit 1
fi

echo "Installing/Updating dependencies..."
pip install -r requirements.txt

echo "Checking Playwright browsers..."
playwright install

echo "Starting Social Bot..."
python main.py

read -p "Press Enter to exit..."
