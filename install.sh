#!/usr/bin/env bash
# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# MUTANTE — Continuous Adversarial Semiotic Evaluator
# Installation script
# Usage: bash install.sh

set -euo pipefail

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
ok()   { echo -e "${G}  ✓${N} $1"; }
warn() { echo -e "${Y}  ⚠${N} $1"; }
err()  { echo -e "${R}  ✗${N} $1"; exit 1; }

echo ""
echo "MUTANTE — Continuous Adversarial Semiotic Evaluator"
echo "Installation"
echo ""

# Python version check (3.10+)
command -v python3 >/dev/null 2>&1 || err "python3 not found"
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
PY_MIN=$(echo "$PY_VER" | cut -d. -f2)
[[ "$PY_MAJ" -ge 3 && "$PY_MIN" -ge 10 ]] || err "Python 3.10+ required (found $PY_VER)"
ok "Python $PY_VER"

# Virtual environment
if [ ! -d .venv ]; then
    python3 -m venv .venv
    ok ".venv created"
else
    ok ".venv already exists"
fi

# shellcheck source=/dev/null
source .venv/bin/activate
ok "Virtual environment activated"

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Dependencies installed"

# .env setup
if [ ! -f .env ]; then
    cat > .env <<'ENVEOF'
GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
VERTEX_AI_LOCATION="us-central1"
ELASTIC_CLOUD_ID="your-elastic-cloud-id"
ELASTIC_API_KEY="your-elastic-api-key"
TARGET_MODEL="gemini-3-flash"
ENVEOF
    warn ".env created — fill in your credentials before running"
else
    ok ".env already exists"
fi

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  python run_campaign.py --limit 500        # capped test run"
echo "  python run_campaign.py                    # full campaign (~32 000 prompts)"
echo "  streamlit run dashboard/app.py            # web dashboard on :8501"
echo "  python mcp_mutante.py                     # MCP server"
