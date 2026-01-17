#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "⚡ Initializing UI & Visuals Developer Persona..."

# Check Python
if ! command_exists python3; then
    echo "❌ Python3 is not installed."
    exit 1
fi

# Check Pip
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "❌ pip is not installed."
    echo "👉 Please run: sudo apt install python3-pip"
    exit 1
fi

echo "📦 Installing Dependencies..."
python3 -m pip install -r dashboard/requirements.txt

echo "🚀 Launching Command Center..."
python3 -m streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --theme.base "dark"
