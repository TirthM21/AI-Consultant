#!/bin/bash

echo "========================================"
echo "AI Consultant Agent - Quick Setup"
echo "========================================"
echo ""

echo "[1/4] Installing Python dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "SUCCESS: Dependencies installed"
echo ""

echo "[2/4] Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "WARNING: Please edit .env file with your email settings"
    echo ""
fi
echo "SUCCESS: Environment ready"
echo ""

echo "[3/4] Database will be auto-created on first run..."
echo ""

echo "[4/4] Starting Flask application..."
python3 app.py