#!/bin/bash

echo "================================================="
echo " Stopping Portfolio Analyzer Live Dashboard"
echo "================================================="

# Kill uvicorn/backend
BACKEND_PIDS=$(ps aux | grep "live-analyzer/venv/bin/python3" | grep -v grep | awk '{print $2}')
if [ -n "$BACKEND_PIDS" ]; then
    echo "Stopping Backend PIDs: $BACKEND_PIDS"
    kill $BACKEND_PIDS
else
    echo "Backend is not running."
fi

# Stop Caddy
echo "Stopping Caddy server..."
/opt/homebrew/bin/caddy stop > /dev/null 2>&1

echo "Servers shut down cleanly."
