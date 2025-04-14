#!/bin/bash

# Start the backend
echo "Starting backend..."
cd backend

# Try python3 first, then fall back to python if python3 is not available
if command -v python3 &>/dev/null; then
    python3 app.py &
else
    python app.py &
fi

BACKEND_PID=$!
cd ..

# Start the frontend
echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Both services are running!"
echo "Frontend: http://localhost:5175"
echo "Backend: http://localhost:5002/api/health"
echo ""
echo "Press Ctrl+C to stop both services"

# Handle termination
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait
