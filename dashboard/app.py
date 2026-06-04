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

"""
app.py — Main Entry Point and Unified Page Router for the MUTANTE Security Dashboard.

TECHNICAL ARCHITECTURE NOTE:
This module initializes the Streamlit runtime state, enforces layout containment metrics,
and serves as the central router for the forensic visualization suite. It dynamically
resolves workspace directories to prevent namespace collision across standalone deployment segments.

Execution Context:
    streamlit run dashboard/app.py
"""

import sys
import os
import streamlit as st

# Dynamic workspace path resolution to handle multi-tiered directory structures gracefully
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.dirname(os.path.abspath(__file__))

for p in (ROOT, DASHBOARD):
    if p not in sys.path:
        sys.path.insert(0, p)

from components.css import inject, force_sidebar_open
from components.sidebar import render

# Strict application configuration targeting professional high-definition layout displays
st.set_page_config(
    page_title="MUTANTE — Semantic Safety Diagnostics",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global stylesheet injection and structural containment configuration
inject()
force_sidebar_open()
active_page = render()

# Dynamic view routing mechanism decoupled from hardcoded page layouts
if active_page == "command_center":
    from pages.command_center import render as page
    page()
elif active_page == "forensic_feed":
    from pages.forensic_feed import render as page
    page()
elif active_page == "analytics":
    from pages.analytics import render as page
    page()
elif active_page == "agent_console":
    from pages.agent_console import render as page
    page()
elif active_page == "attack_families":
    from pages.attack_families import render as page
    page()
