#!/bin/bash

# Define project root
PROJECT_ROOT="$(dirname "$(readlink -f "$0")")"
echo "Project root: $PROJECT_ROOT"

# Start Backend
echo "Starting FastAPI backend server..."
cd "$PROJECT_ROOT"
source venv/bin/activate || {
    echo "Failed to activate Python virtual environment. Make sure it exists."
    exit 1
}

cd "$PROJECT_ROOT/backend"
python run.py --port 8001 &
BACKEND_PID=$!
echo "Backend started with PID $BACKEND_PID"

# Wait a moment to ensure backend starts
sleep 2

# Start Frontend
echo "Starting React frontend..."
cd "$PROJECT_ROOT/frontend"
if [ ! -f package.json ]; then
    echo "Error: package.json not found in $(pwd)"
    kill $BACKEND_PID
    exit 1
fi

# Check if node_modules exists, install if needed
if [ ! -d node_modules ]; then
    echo "Installing node modules..."
    npm install
fi

echo "Starting npm..."
npm run start &
FRONTEND_PID=$!

# Handle shutdown of both processes when script is terminated
trap 'echo "Stopping servers..."; kill $FRONTEND_PID; kill $BACKEND_PID; exit' INT TERM EXIT

# Keep the script running
echo "Development servers are running."
echo "- Frontend: http://localhost:3000"
echo "- Backend: http://localhost:8001"
echo "Press Ctrl+C to stop."
wait