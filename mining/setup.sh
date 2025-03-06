#!/bin/bash

# Remove old venv if it exists
if [ -d ".venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf .venv
fi

# Use Python 3.12 if available
if command -v python3.12 &> /dev/null; then
    echo "Using Python 3.12"
    python3.12 -m venv .venv
else
    echo "Python 3.12 not found, using default Python3"
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
pip3 install -r requirements.txt

echo "Mining tools virtual environment setup complete"
echo "To activate the environment in the future, run:"
echo "source .venv/bin/activate"