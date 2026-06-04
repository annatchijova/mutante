#!/usr/bin/env bash
# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# MUTANTE — Automated Pipeline Installation & Synchronization Suite (2026)
# Usage: bash install.sh [custom_source_directory_path]
#
# Architectural Note: 
# This runner automates structural patch distribution, verifies syntax correctness across 
# core evaluation modules, and triggers the offline validation suite inside the virtual environment.

set -euo pipefail

MUTANTE_DIR="/home/labestiadevigia/MUTANTE"
SRC="${1:-${HOME}/Downloads}"

# Standard Terminal Output ANSI Color Layout Configuration
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
ok()   { echo -e "${G}  ✓${N} $1"; }
warn() { echo -e "${Y}  ⚠${N} $1"; }
err()  { echo -e "${R}  ✗${N} $1"; }

echo ""
echo "MUTANTE Pipeline Automation Deployment Suite"
echo "Target Workspace Repository: $MUTANTE_DIR"
echo "Source Artifacts Directory:  $SRC"
echo ""

# 1. Structural Target Workspace Directory Verification
for dir in \
    "$MUTANTE_DIR" \
    "$MUTANTE_DIR/agent_mutante/engine" \
    "$MUTANTE_DIR/dashboard/pages" \
    "$MUTANTE_DIR/dashboard/components"; do
    if [ ! -d "$dir" ]; then
        err "Critical layout failure: Directory not found -> $dir"
        exit 1
    fi
done

# 2. Source Patch Package Validation Layer
CRITICAL_FILES=(
    "main.py"
    "requirements.txt"
    ".gitignore"
    "elastic_semantic.py"
    "mutante_hybrid_evaluator.py"
    "semiotic_llm_judge.py"
    "app.py"
    "attack_families.py"
    "analytics.py"
    "agent_console.py"
    "sidebar.py"
    "test_demo_pipeline.py"
)

MISSING_COUNT=0
for f in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$SRC/$f" ]; then
        warn "Staged update file not detected in source directory: $f"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

if [ "$MISSING_COUNT" -eq "${#CRITICAL_FILES[@]}" ]; then
    err "Aborting deployment: No upgraded structural components detected at source path."
    exit 1
fi

# 3. Synchronizing Framework Configuration and Core Orchestrator Layouts
echo "Synchronizing root environment and core orchestrator layers..."
for f in "main.py" "requirements.txt" ".gitignore"; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$MUTANTE_DIR/"
        ok "$f successfully synchronized."
    fi
done

# 4. Synchronizing Backend Semiotic and Evaluation Engines
echo "Synchronizing backend semiotic mutation and evaluation modules..."
for f in "elastic_semantic.py" "mutante_hybrid_evaluator.py" "semiotic_llm_judge.py"; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$MUTANTE_DIR/agent_mutante/engine/"
        ok "$f successfully routed to engine package."
    fi
done

# 5. Synchronizing Streamlit Dashboard Core and View Routers
echo "Synchronizing view interfaces and web application layouts..."
if [ -f "$SRC/app.py" ]; then
    cp "$SRC/app.py" "$MUTANTE_DIR/dashboard/"
    ok "app.py core layout updated."
fi

for f in "attack_families.py" "analytics.py" "agent_console.py"; do
    if [ -f "$SRC/$f" ]; then
        cp "$SRC/$f" "$MUTANTE_DIR/dashboard/pages/"
        ok "$f view router synchronized."
    fi
done

if [ -f "$SRC/sidebar.py" ]; then
    cp "$SRC/sidebar.py" "$MUTANTE_DIR/dashboard/components/"
    ok "sidebar.py navigation element updated."
fi

# 6. Synchronizing Pre-flight Validation Components
echo "Synchronizing testing framework elements..."
if [ -f "$SRC/test_demo_pipeline.py" ]; then
    cp "$SRC/test_demo_pipeline.py" "$MUTANTE_DIR/"
    ok "test_demo_pipeline.py synchronized."
fi

# 7. Virtual Environment Invocation and Static Syntax Evaluation
echo "Activating runtime isolated environment and compiling Python modules..."
export VIRTUAL_ENV="$MUTANTE_DIR/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

if [ ! -f "$VIRTUAL_ENV/bin/python3" ]; then
    err "Deployment Alert: Python executable not found within the expected virtual environment path: $VIRTUAL_ENV/bin/python3"
    exit 1
fi

echo "Executing python compilation validation..."
SYNTAX_OK=0; SYNTAX_FAIL=0
TARGET_COMPILATION_FILES=(
    "$MUTANTE_DIR/main.py"
    "$MUTANTE_DIR/agent_mutante/engine/semiotic_llm_judge.py"
    "$MUTANTE_DIR/agent_mutante/engine/mutante_hybrid_evaluator.py"
    "$MUTANTE_DIR/agent_mutante/engine/elastic_semantic.py"
    "$MUTANTE_DIR/dashboard/pages/attack_families.py"
    "$MUTANTE_DIR/dashboard/pages/analytics.py"
    "$MUTANTE_DIR/dashboard/pages/agent_console.py"
    "$MUTANTE_DIR/test_demo_pipeline.py"
)

for f in "${TARGET_COMPILATION_FILES[@]}"; do
    if [ -f "$f" ]; then
        if python3 -m py_compile "$f" 2>/dev/null; then
            ok "$(basename "$f") successfully compiled."
            SYNTAX_OK=$((SYNTAX_OK + 1))
        else
            err "$(basename "$f") failed verification: Bytecode compilation error."
            SYNTAX_FAIL=$((SYNTAX_FAIL + 1))
        fi
    fi
done

# 8. Automated Triggering of the Offline Test Suite
echo "Launching local offline pipeline verification suite..."
cd "$MUTANTE_DIR"
if python3 test_demo_pipeline.py; then
    ok "Offline operational verification completed successfully."
else
    warn "Test Suite Alert: Failures or exceptions intercepted during verification run."
fi

echo ""
echo "MUTANTE Deployment Report Summary"
echo "Successful Bytecode Compilations: $SYNTAX_OK"
echo "Failed Bytecode Compilations:     $SYNTAX_FAIL"
echo ""

if [ "$SYNTAX_FAIL" -eq 0 ]; then
    echo "Deployment operation finalized successfully. System is stable and ready for live execution."
else
    warn "Deployment completed with outstanding syntax errors. Review compiling logs before launching production servers."
fi
