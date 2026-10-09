#!/bin/bash
echo "==================================================="
echo "Binary Brain IMS - Linux/macOS Quick Installer"
echo "==================================================="

echo "[1/3] Creating virtual environment..."
python3 -m venv venv

echo "[2/3] Activating venv and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "[3/3] Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example."
else
    echo ".env file already exists."
fi

echo ""
echo "==================================================="
echo "Installation Complete!"
echo "You can now run the app with:"
echo "source venv/bin/activate"
echo "python main.py"
echo "==================================================="
