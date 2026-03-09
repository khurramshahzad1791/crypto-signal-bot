#!/bin/bash
# start.sh – run Streamlit only (ML training disabled for now)

# Start Streamlit in foreground
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
