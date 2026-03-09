#!/bin/bash
# start.sh – run Streamlit and periodic training

# Start Streamlit in background
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &

# Run training every 24 hours
while true; do
    sleep 86400  # 24 hours
    python -c "from learner import StrategyLearner; StrategyLearner().train()"
done
