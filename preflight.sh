#!/bin/bash
echo "--- Starting Infrastructure Verification ---"
source .venv/bin/activate

# Ensure Environment
export MUTANTE_SEMANTIC_INDEX="mutante-semantic"

# 1. Populate demo data if empty
echo "Populating index with forensic demo data..."
python3 generate_demo_dataset.py

# 2. Launch Dashboard
echo "Launching Forensic Dashboard..."
streamlit run dashboard/app.py
