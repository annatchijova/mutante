#!/usr/bin/env bash

# MUTANTE — Download of evaluation datasets from public sources

# Datasets are NOT included in the repo to reduce the risk of malicious use.

# This script downloads them from their original repositories with attribution.

# Usage: bash scripts/download_datasets.sh

set -euo pipefail

MUTANTE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$MUTANTE_DIR"

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
ok()   { echo -e "${G}  ✓${N} $1"; }
warn() { echo -e "${Y}  ⚠${N} $1"; }

echo ""
echo " MUTANTE — Dataset Download"
echo " Documented public sources for red-teaming research"
echo ""

# Source 1: msoedov/agentic_security

# 7,251 adversarial prompts for LLM agents

# License: MIT

# [https://github.com/msoedov/agentic_security](https://github.com/msoedov/agentic_security)

echo "[1/3] msoedov/agentic_security"
if [ ! -f "$DATA_DIR/jailbreaks_dataset_master_11k.csv" ]; then
curl -sL 

"[https://raw.githubusercontent.com/msoedov/agentic_security/main/agentic_security/sensitive_data/data.csv](https://www.google.com/search?q=https%3A%2F%2Fraw.githubusercontent.com%2Fmsoedov%2Fagentic_security%2Fmain%2Fagentic_security%2Fsensitive_data%2Fdata.csv)" 

-o "$DATA_DIR/jailbreaks_dataset_master_11k.csv"
ok "jailbreaks_dataset_master_11k.csv downloaded"
else
warn "jailbreaks_dataset_master_11k.csv already exists, skipped"
fi

# Source 2: HarmBench

# Standard benchmark for LLM safety evaluation

# License: MIT

# [https://github.com/centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench)

echo "[2/3] centerforaisafety/HarmBench"
if [ ! -f "$DATA_DIR/harmbench_behaviors.csv" ]; then
curl -sL 

"[https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/data/behavior_datasets/harmbench_behaviors_text_val.csv](https://www.google.com/search?q=https%3A%2F%2Fraw.githubusercontent.com%2Fcenterforaisafety%2FHarmBench%2Fmain%2Fdata%2Fbehavior_datasets%2Fharmbench_behaviors_text_val.csv)" 

-o "$DATA_DIR/harmbench_behaviors.csv"
ok "harmbench_behaviors.csv downloaded"
else
warn "harmbench_behaviors.csv already exists, skipped"
fi

# Source 3: Third source

# TODO: complete with the URL of the third source repository

# echo "[3/3] "

# curl -sL "" -o "$DATA_DIR/jailbreaks_dataset.csv"

echo ""
echo " Datasets downloaded to: $DATA_DIR"
echo ""
echo " NOTE: These datasets are for LLM defensive security"
echo " research only. See README for full attribution"
echo " and terms of use."
echo ""
echo " Next step:"
echo " DATASET_PATH=jailbreaks_dataset_master_11k.csv python3 main.py"
