#!/bin/bash

# Port Config
BACKEND_PORT=8000
FRONTEND_PORT=3000

echo "================================================="
echo " Starting Portfolio Analyzer Live Dashboard (Prod)"
echo "================================================="

# Navigate to project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

# 1. Activate backend virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r backend/requirements.txt
fi

# Check if backend is already running
if ps aux | grep "live-analyzer/venv/bin/python3" | grep -v grep > /dev/null; then
    echo "Backend is already running."
else
    echo "Starting Backend API on http://127.0.0.1:$BACKEND_PORT..."
    ./venv/bin/python3 backend/run.py > backend.log 2>&1 &
    sleep 2
fi

# 2. Start Caddy server
echo "Starting Caddy server on http://localhost:$FRONTEND_PORT..."
/opt/homebrew/bin/caddy start --config Caddyfile > caddy.log 2>&1

echo "-------------------------------------------------"
echo "Dashboards are active!"
echo "Open Live Analyzer (Kite Connected): http://localhost:3000"
echo "Open Static Analyzer (Drag & Drop XLSX): http://localhost:3001"
echo "To stop the servers, run: ./stop-live.sh"
echo "-------------------------------------------------"
