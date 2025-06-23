#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the llama-factory virtual environment
source "$SCRIPT_DIR/llama-factory-venv/bin/activate"

# Launch the webui with public sharing enabled
GRADIO_SHARE=1 llamafactory-cli webui