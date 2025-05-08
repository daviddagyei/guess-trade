#!/bin/bash

# Start Backend
echo "Starting FastAPI backend server..."
cd "$(dirname "$0")"
source venv/bin/activate
cd backend
python run.py &
BACKEND_PID=$!

# Wait a moment to ensure backend starts
sleep 2

# Start Frontend
echo "Starting React frontend..."
cd "$(dirname "$0")/frontend"
npm start &
FRONTEND_PID=$!

# Handle shutdown of both processes when script is terminated
trap 'echo "Stopping servers..."; kill $FRONTEND_PID; kill $BACKEND_PID; exit' INT TERM EXIT

# Keep the script running
echo "Development servers are running. Press Ctrl+C to stop."
wait