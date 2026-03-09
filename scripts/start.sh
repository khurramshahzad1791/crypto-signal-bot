#!/bin/bash
# Start both FastAPI (background) and Streamlit (foreground)

# Run FastAPI in background
uvicorn orchestrator:app --host 0.0.0.0 --port 8000 &

# Run Streamlit in foreground (so Railway knows it's alive)
streamlit run orchestrator.py --server.port=8501 --server.address=0.0.0.0
