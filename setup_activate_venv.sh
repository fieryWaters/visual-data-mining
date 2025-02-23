#!/bin/bash

# Change to script's directory
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d "venv" ]; then
    python3.11 -m venv venv || python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

source venv/bin/activate
