#!/bin/bash

# Remove old venv if it exists
if [ -d "mining-venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf mining-venv
fi

# Use Python 3.12 if available
if command -v python3.12 &> /dev/null; then
    echo "Using Python 3.12"
    python3.12 -m venv mining-venv
else
    echo "Python 3.12 not found, using default Python3"
    python3 -m venv mining-venv
fi

# Activate virtual environment
source mining-venv/bin/activate

# Install requirements
pip install -r requirements.txt

echo "Mining tools virtual environment setup complete"
echo "To activate the environment in the future, run:"
echo "source mining-venv/bin/activate"