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
css.py — Single source of truth for all MUTANTE styles.
Maintains the forensic aesthetic (Lilac/Yellow, Cinzel and Share Tech Mono fonts).
"""

import streamlit as st

COLORS = {
    "bg":           "#0C0A14",
    "bg2":          "#131020",
    "bg3":          "#1A1530",
    "lila":         "#B07FFF",
    "lila_bright":  "#D4AAFF",
    "lila_dim":     "#6A4A99",
    "lila_glow":    "rgba(176,127,255,0.35)",
    "yellow":       "#FFE033",
    "yellow_dim":   "#B89E00",
    "yellow_glow":  "rgba(255,224,51,0.35)",
    "red":          "#FF4466",
    "red_glow":     "rgba(255,68,102,0.35)",
    "green":        "#00FFB2",
    "cyan":         "#00E5FF",
    "text":         "#E8DFFF",       # FIX 1: más brillante (era #D8CCFF)
    "text_dim":     "#8A7AAA",       # FIX 1: más legible (era #5A4A7A)
    "border":       "#3A2A5A",       # FIX 1: más visible (era #2A1F45)
}

FONTS = {
    "head": "'Cinzel', serif",
    "mono": "'Share Tech Mono', monospace",
    "body": "'Rajdhani', sans-serif",
}

_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;600&display=swap');

:root {{
    --bg:         {bg};
    --bg2:        {bg2};
    --bg3:        {bg3};
    --lila:       {lila};
    --lila-bright:{lila_bright};
    --lila-dim:   {lila_dim};
    --lila-glow:  {lila_glow};
    --yellow:     {yellow};
    --yellow-dim: {yellow_dim};
    --yellow-glow:{yellow_glow};
    --red:        {red};
    --cyan:       {cyan};
    --green:      {green};
    --text:       {text};
    --text-dim:   {text_dim};
    --border:     {border};
    --font-head:  {font_head};
    --font-mono:  {font_mono};
    --font-body:  {font_body};
}}

html, body, [data-testid="stAppViewContainer"] {{
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
}}

/* Scanline effect — sutil, da profundidad */
[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 3px,
        rgba(176,127,255,0.015) 3px,
        rgba(176,127,255,0.015) 4px
    );
    pointer-events: none;
    z-index: 0;
}}

[data-testid="stHeader"], [data-testid="stToolbar"], footer {{
    display: none !important;
}}

/* FIX: ocultar nav nativa de Streamlit */
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNav"] {{
    display: none !important;
}}

.block-container {{
    padding: 2rem 3rem !important;
    max-width: 1400px !important;
}}

h1, h2, h3 {{
    font-family: var(--font-head) !important;
    color: var(--lila-bright) !important;
    letter-spacing: 0.08em !important;
}}

/* FIX 2: Métricas — labels más legibles */
[data-testid="metric-container"] {{
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 3px !important;
    padding: 1rem 1.4rem !important;
    position: relative !important;
    overflow: hidden !important;
}}

[data-testid="metric-container"]::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--lila), transparent);
}}

[data-testid="stMetricLabel"] {{
    font-family: var(--font-mono) !important;
    font-size: 0.68rem !important;
    color: var(--lila-bright) !important;    /* FIX: era text_dim, casi invisible */
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    opacity: 0.85 !important;
}}

[data-testid="stMetricValue"] {{
    font-family: var(--font-head) !important;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    color: var(--yellow) !important;
    text-shadow: 0 0 18px var(--yellow-glow), 0 0 50px rgba(255,224,51,0.1) !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}}

/* FIX 3: Nav buttons — más contraste y visibilidad */
[data-testid="stSidebar"] button {{
    font-family: var(--font-mono) !important;
    letter-spacing: 0.08em !important;
    color: var(--text) !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    transition: all 0.15s ease !important;
    font-size: 0.82rem !important;
}}

[data-testid="stSidebar"] button:hover {{
    border-color: var(--lila-dim) !important;
    color: var(--lila-bright) !important;
    background: var(--bg3) !important;
}}

.nav-active button {{
    background: var(--bg3) !important;
    border-left: 3px solid var(--yellow) !important;
    border-color: var(--yellow) !important;
    color: var(--yellow) !important;
    text-shadow: 0 0 8px var(--yellow-glow) !important;
}}

/* Botones generales */
button {{
    font-family: var(--font-mono) !important;
    letter-spacing: 0.1em !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    background: var(--bg) !important;
    transition: all 0.15s ease !important;
}}

button:hover {{
    border-color: var(--lila) !important;
    color: var(--lila-bright) !important;
}}

/* FIX 4: Badges/indicadores semióticos — mejor contraste */
.indicator-badge {{
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: #FFFFFF;
    background: transparent;
    border: 1px solid var(--lila-dim);
    border-radius: 2px;
    padding: 0.2rem 0.6rem;
    margin: 0.2rem 0;
    letter-spacing: 0.05em;
}}

.indicator-badge.danger {{
    border-color: var(--red);
    color: #FFB3C1;
}}

.indicator-badge.bypass {{
    border-color: var(--yellow);
    color: var(--yellow);
    text-shadow: 0 0 6px var(--yellow-glow);
}}

.indicator-badge.negated {{
    border-color: var(--lila-dim);
    color: var(--lila-bright);
    opacity: 0.7;
}}

/* Expanders */
[data-testid="stExpander"] {{
    border: 1px solid var(--border) !important;
    background: var(--bg2) !important;
    border-radius: 2px !important;
}}

[data-testid="stExpander"]:hover {{
    border-color: var(--lila-dim) !important;
}}

/* Selectbox y sliders */
[data-testid="stSelectbox"] > div {{
    background: var(--bg2) !important;
    border-color: var(--border) !important;
}}

/* Code blocks */
code, pre {{
    font-family: var(--font-mono) !important;
    background: var(--bg3) !important;
    color: var(--lila-bright) !important;
    border: 1px solid var(--border) !important;
    font-size: 0.78rem !important;
}}

/* Section headers */
.section-header {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 1rem 0 0.5rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}}
.section-header-icon {{
    color: var(--lila);
    font-size: 1.2rem;
}}
.section-header-title {{
    font-family: var(--font-head);
    font-size: 1.4rem;
    color: var(--lila-bright);
    letter-spacing: 0.15em;
    text-transform: uppercase;
}}
.section-header-sub {{
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-left: auto;
}}

/* Pulse dot animado */
@keyframes pulse-lila {{
    0% {{ box-shadow: 0 0 0 0 var(--lila-glow); }}
    70% {{ box-shadow: 0 0 0 10px rgba(176,127,255,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(176,127,255,0); }}
}}
.pulse-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse-lila 2s ease-in-out infinite;
    vertical-align: middle;
    margin-right: 5px;
}}

/* Scrollbar custom */
::-webkit-scrollbar {{
    width: 4px;
}}
::-webkit-scrollbar-track {{
    background: var(--bg);
}}
::-webkit-scrollbar-thumb {{
    background: var(--lila-dim);
    border-radius: 2px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: var(--lila);
}}
"""

def inject() -> None:
    """Injects base CSS. Must be called at the start of every page."""
    css = _BASE_CSS.format(
        **COLORS,
        font_head=FONTS["head"],
        font_mono=FONTS["mono"],
        font_body=FONTS["body"],
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def section_header(icon: str, title: str, sub: str = "") -> None:
    """Renders a section header with standardized styling."""
    sub_html = f'<span class="section-header-sub">{sub}</span>' if sub else ""
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-header-icon">{icon}</span>'
        f'<span class="section-header-title">{title}</span>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

def force_sidebar_open() -> None:
    st.markdown(
        """<style>
        [data-testid="collapsedControl"] { 
            display: flex !important;
            opacity: 1 !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )
