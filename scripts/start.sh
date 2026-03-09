#!/bin/bash
# Start script for Railway deployment

echo "Starting Integrated Trading System..."

# Create necessary directories
mkdir -p /app/data /app/logs /app/models

# Start the main orchestrator (API + background tasks)
python orchestrator.py &

# Start Streamlit dashboard in background
streamlit run orchestrator.py dashboard --server.port=8501 --server.address=0.0.0.0 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
