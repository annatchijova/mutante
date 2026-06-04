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
sidebar.py — Persistent Side Navigation Component for the Streamlit UI Framework.

TECHNICAL APPLICATION NOTE:
This component handles the reactive runtime navigation system of the security dashboard.
It manages state serialization dynamically inside `st.session_state["active_page"]`.
To ensure visual consistency across rapid structural updates and recorded execution flows,
it leverages asynchronous rerun flags instantly upon tracking navigation updates.
"""

import os
import base64
from pathlib import Path
import streamlit as st

PAGES = [
    {"key": "command_center", "icon": "◈", "label": "Command Center"},
    {"key": "forensic_feed",  "icon": "⬡", "label": "Forensic Feed"},
    {"key": "analytics",      "icon": "◉", "label": "Analytics"},
    {"key": "agent_console",  "icon": "✦", "label": "Agent Console"},
    {"key": "attack_families", "icon": "⬢", "label": "Attack Families"},
]


def _load_logo() -> str:
    """
    Resolves the layout-agnostic workspace pathway and safely extracts the asset image.
    Encodes the file into an inline Base64 HTML string to bypass local caching problems.
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    logo_path = base_dir / "assets" / "logo.png"
    
    if not logo_path.exists():
        return ""
        
    try:
        with open(logo_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""


def render() -> str:
    """
    Renders the persistent side control deck and handles navigation routing state updates.
    Returns the active target page identifier key.
    """
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "command_center"

    with st.sidebar:
        logo_data = _load_logo()
        
        if logo_data:
            st.markdown(
                f'<div style="text-align: center; padding-bottom: 0.5rem;">'
                f'<img src="{logo_data}" style="width: 75px; height: auto;">'
                f'</div>',
                unsafe_allow_html=True,
            )
            
        st.markdown(
            '<div style="text-align: center; margin-bottom: 2rem;">'
            '<div style="font-family:Cinzel,serif;font-size:1.4rem;color:#D4AAFF;letter-spacing:0.15em;">MUTANTE</div>'
            '<div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:#5A4A7A;letter-spacing:0.2em;">'
            'SEMANTIC SAFETY LAB</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Dynamic loop rendering for target application views
        for page in PAGES:
            is_active = st.session_state["active_page"] == page["key"]
            label = f"{page['icon']}  {page['label']}"

            if is_active:
                st.markdown('<div class="nav-active">', unsafe_allow_html=True)
            
            if st.button(label, key=f"nav_{page['key']}", use_container_width=True):
                st.session_state["active_page"] = page["key"]
                st.rerun()
                
            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>" * 6, unsafe_allow_html=True)
        
        # NOTE: Divisor line replaced with structural blank space spacing blocks to keep UI style guidelines intact
        st.markdown(
            '<div style="font-family:Share Tech Mono,monospace;font-size:0.48rem;'
            'color:#241A36;letter-spacing:0.1em;line-height:2;padding:0 0.2rem;text-align:center;">'
            'Vertex AI &nbsp;·&nbsp; Elasticsearch &nbsp;·&nbsp; MCP Layer<br>'
            'Production Framework Model: 2026'
            '</div>',
            unsafe_allow_html=True,
        )

    return st.session_state["active_page"]
