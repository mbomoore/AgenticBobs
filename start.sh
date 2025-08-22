#!/bin/bash

# Start script for The Bobs 2.0
# This script starts both the backend and frontend development servers

echo "Starting The Bobs 2.0..."

# Check if we're in the right directory
if [ ! -f "backend/main.py" ] || [ ! -f "thebobs/package.json" ]; then
    echo "Error: Please run this script from the AgenticBobs project root directory"
    exit 1
fi

# Function to handle cleanup on script exit
cleanup() {
    echo "Stopping servers..."
    jobs -p | xargs -r kill
    exit 0
}

# Set up trap to handle Ctrl+C
trap cleanup SIGINT

# Start backend server in background
echo "Starting backend server on http://localhost:8000..."
cd backend
uv run python dev_server.py &
BACKEND_PID=$!
cd ..

# Give backend a moment to start
sleep 2

# Start frontend development server in background
echo "Starting frontend server on http://localhost:5173..."
cd thebobs
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "🚀 The Bobs 2.0 is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for any process to finish
wait
