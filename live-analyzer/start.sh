#!/bin/bash

# Port Config
BACKEND_PORT=8000
FRONTEND_PORT=5173

echo "==============================================="
echo " Starting Personal Portfolio Analyzer Dashboard"
echo "==============================================="

# Navigate to project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

# 1. Activate backend virtual environment and run Uvicorn
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r backend/requirements.txt
fi

echo "Starting Backend API on http://127.0.0.1:$BACKEND_PORT..."
./venv/bin/python3 backend/run.py > backend.log 2>&1 &
BACKEND_PID=$!

# 2. Start frontend dev server
echo "Starting Frontend Dev Server on http://localhost:$FRONTEND_PORT..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Trap Ctrl+C (SIGINT) to kill both background processes on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers shut down cleanly."
    exit
}
trap cleanup SIGINT

echo "-----------------------------------------------"
echo "Dashboard is launching!"
echo "Open: http://localhost:$FRONTEND_PORT"
echo "Press Ctrl+C to terminate both servers."
echo "-----------------------------------------------"

# Wait for background processes to keep script running
wait
