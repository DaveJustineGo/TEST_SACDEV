#!/bin/bash

# Ensure required system packages are installed
sudo apt update
sudo apt install -y python3-venv python3-pip python3-full

# Create virtual environment if it doesn't exist
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

pip install -r requirements.txt


echo
# Default port
PORT=5000

# Check for UFW
if ! command -v ufw &> /dev/null; then
    echo "UFW is not installed. Installing..."
    sudo apt update && sudo apt install -y ufw
fi

# Enable UFW if not already enabled
STATUS=$(sudo ufw status | grep -o "Status: active")
if [ "$STATUS" != "Status: active" ]; then
    echo "Enabling UFW..."
    sudo ufw enable
else
    echo "UFW is already active."
fi

# Allow the specified port and http port
echo "Allowing port $PORT through firewall..."
sudo ufw allow $PORT
sudo ufw allow 80


echo "✅ All packages installed in virtual environment."