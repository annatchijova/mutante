# Copyright 2026 Anna Tchijova, Olga Vasilieva, Gemini
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
css.py — Single source of truth for the MUTANTE forensic console aesthetic.

DESIGN LANGUAGE
---------------
The dashboard reads as a precision forensic instrument, not a generic dashboard.
Three devices carry that identity:

  1. An evidence grid — a faint graph-paper dot field behind everything, the way
     measurement instruments are read against a calibrated background.
  2. Corner brackets — L-shaped reticle ticks on every data surface, so panels feel
     framed and sighted rather than floated.
  3. A disciplined two-accent code where colour means something:
        amber  -> signal detected / bypass (the thing being hunted)
        lila   -> system, structure, process
        rose   -> threat
        mint   -> resisted / healthy
        ice    -> secondary signal / info

Typography keeps Cinzel as a rare, deliberate display face (used only for the
wordmark, page titles, verdict words and headline values — its inscriptional
weight evokes a standard of evidence) over a Share Tech Mono instrument readout.
All original COLORS keys are preserved so existing pages keep working unchanged.
"""

import streamlit as st

COLORS = {
    # --- original keys (refined values, all preserved for backward-compat) ---
    "bg":           "#0A0813",
    "bg2":          "#110D1E",
    "bg3":          "#181226",
    "lila":         "#B07FFF",
    "lila_bright":  "#D9B8FF",
    "lila_dim":     "#6B4FA0",
    "lila_glow":    "rgba(176,127,255,0.35)",
    "yellow":       "#FFD93D",
    "yellow_dim":   "#7A6410",
    "yellow_glow":  "rgba(255,217,61,0.38)",
    "red":          "#FF4D6D",
    "red_glow":     "rgba(255,77,109,0.35)",
    "green":        "#3DF5C0",
    "cyan":         "#6FE3FF",
    "text":         "#ECE4FF",
    "text_dim":     "#9282B5",
    "border":       "#2E2348",
    # --- new semantic aliases used by the upgraded components ---
    "void":         "#0A0813",
    "panel":        "#110D1E",
    "panel2":       "#181226",
    "line":         "#2E2348",
    "line_soft":    "rgba(176,127,255,0.10)",
    "amber":        "#FFD93D",
    "rose":         "#FF4D6D",
    "mint":         "#3DF5C0",
    "ice":          "#6FE3FF",
    "bone":         "#ECE4FF",
    "bone_dim":     "#9282B5",
    "bone_faint":   "#5C5278",
}

FONTS = {
    "head": "'Cinzel', serif",
    "mono": "'Share Tech Mono', monospace",
    "body": "'Rajdhani', sans-serif",
}

# Maps a verdict to (accent css-var, label)
_VERDICT_META = {
    "BYPASSED":  ("var(--amber)", "BYPASSED"),
    "UNCERTAIN": ("var(--lila-bright)", "UNCERTAIN"),
    "BLOCKED":   ("var(--bone-faint)", "BLOCKED"),
}

_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&display=swap');

:root {{
    --bg:          {bg};
    --bg2:         {bg2};
    --bg3:         {bg3};
    --void:        {void};
    --panel:       {panel};
    --panel2:      {panel2};
    --lila:        {lila};
    --lila-bright: {lila_bright};
    --lila-dim:    {lila_dim};
    --lila-glow:   {lila_glow};
    --yellow:      {yellow};
    --yellow-dim:  {yellow_dim};
    --yellow-glow: {yellow_glow};
    --amber:       {amber};
    --red:         {red};
    --rose:        {rose};
    --cyan:        {cyan};
    --ice:         {ice};
    --green:       {green};
    --mint:        {mint};
    --text:        {text};
    --text-dim:    {text_dim};
    --bone:        {bone};
    --bone-dim:    {bone_dim};
    --bone-faint:  {bone_faint};
    --line:        {line};
    --line-soft:   {line_soft};
    --border:      {border};
    --font-head:   {font_head};
    --font-mono:   {font_mono};
    --font-body:   {font_body};
}}

/*  base */
html, body, [data-testid="stAppViewContainer"] {{
    background-color: var(--void) !important;
    color: var(--bone) !important;
    font-family: var(--font-body) !important;
}}

/* Evidence grid + scanline atmosphere (the instrument-readout background) */
[data-testid="stAppViewContainer"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        radial-gradient(circle at center, rgba(176,127,255,0.085) 0.7px, transparent 0.7px),
        radial-gradient(circle at center, rgba(176,127,255,0.085) 0.7px, transparent 0.7px);
    background-size: 24px 24px, 24px 24px;
    background-position: 0 0, 12px 12px;
    pointer-events: none;
    z-index: 0;
}}
[data-testid="stAppViewContainer"]::after {{
    content: '';
    position: fixed;
    inset: 0;
    background:
        repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(176,127,255,0.012) 3px, rgba(176,127,255,0.012) 4px),
        radial-gradient(ellipse 90% 70% at 50% 0%, rgba(176,127,255,0.06), transparent 60%);
    pointer-events: none;
    z-index: 0;
}}

[data-testid="stHeader"], [data-testid="stToolbar"], footer {{
    display: none !important;
}}
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNav"] {{
    display: none !important;
}}

::selection {{ background: var(--amber); color: var(--void); }}

.block-container {{
    padding: 2.2rem 3rem 4rem !important;
    max-width: 1480px !important;
    position: relative;
    z-index: 1;
}}

/* Orchestrated page-load reveal — one quiet, deliberate moment. */
@keyframes mt-rise {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.block-container > div > div > [data-testid="stVerticalBlock"] > div {{
    animation: mt-rise 0.5s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}}

h1, h2, h3 {{
    font-family: var(--font-head) !important;
    color: var(--lila-bright) !important;
    letter-spacing: 0.06em !important;
    font-weight: 600 !important;
}}

p, span, div, label, li {{ color: var(--bone); }}

/*  section header */
.section-header {{
    display: flex;
    align-items: baseline;
    gap: 0.9rem;
    padding: 0.4rem 0 0.7rem 0.9rem;
    position: relative;
    border-bottom: 1px solid var(--line);
    margin: 0.4rem 0 1.5rem 0;
}}
.section-header::before {{
    content: '';
    position: absolute;
    left: 0; top: 0.55rem; bottom: 0.75rem;
    width: 3px;
    background: linear-gradient(180deg, var(--amber), var(--lila));
    box-shadow: 0 0 10px var(--lila-glow);
}}
.section-header-icon {{
    color: var(--lila);
    font-size: 1.05rem;
    text-shadow: 0 0 10px var(--lila-glow);
}}
.section-header-title {{
    font-family: var(--font-head);
    font-size: 1.32rem;
    color: var(--lila-bright);
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}
.section-header-sub {{
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--bone-dim);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-left: auto;
    border: 1px solid var(--line);
    padding: 0.25rem 0.6rem;
    border-radius: 2px;
}}

/*  metric / instrument */
/* Native st.metric, framed as an instrument cell (in case any page uses it). */
[data-testid="stMetric"], [data-testid="metric-container"] {{
    background:
        linear-gradient(180deg, rgba(176,127,255,0.05), transparent 40%),
        var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: 2px !important;
    padding: 1.1rem 1.3rem !important;
    position: relative !important;
    overflow: hidden !important;
}}
[data-testid="stMetric"]::after, [data-testid="metric-container"]::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--lila), transparent);
}}
[data-testid="stMetricLabel"] {{
    font-family: var(--font-mono) !important;
    font-size: 0.64rem !important;
    color: var(--lila-bright) !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    opacity: 0.82 !important;
}}
[data-testid="stMetricValue"] {{
    font-family: var(--font-head) !important;
    font-size: 2.1rem !important;
    font-weight: 900 !important;
    color: var(--amber) !important;
    text-shadow: 0 0 18px var(--yellow-glow) !important;
}}

/* The custom forensic readout console (replaces the generic metric row). */
.mt-console {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.9rem;
    margin: 0.2rem 0 0.5rem 0;
}}
.mt-cell {{
    position: relative;
    background:
        linear-gradient(180deg, rgba(176,127,255,0.04), transparent 45%),
        var(--panel);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 1.05rem 1.1rem 0.95rem;
    overflow: hidden;
}}
/* Corner reticle brackets (top-left + bottom-right) */
.mt-cell::before, .mt-cell::after {{
    content: '';
    position: absolute;
    width: 11px; height: 11px;
    border-color: var(--accent, var(--lila));
    opacity: 0.85;
}}
.mt-cell::before {{ top: 6px; left: 6px; border-top: 1.5px solid; border-left: 1.5px solid; }}
.mt-cell::after  {{ bottom: 6px; right: 6px; border-bottom: 1.5px solid; border-right: 1.5px solid; }}
.mt-cell .mt-label {{
    font-family: var(--font-mono);
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--bone-dim);
    margin-bottom: 0.5rem;
}}
.mt-cell .mt-value {{
    font-family: var(--font-head);
    font-size: 2.25rem;
    font-weight: 900;
    line-height: 1;
    color: var(--accent, var(--amber));
    text-shadow: 0 0 20px color-mix(in srgb, var(--accent, var(--amber)) 40%, transparent);
}}
.mt-cell .mt-sub {{
    font-family: var(--font-mono);
    font-size: 0.58rem;
    letter-spacing: 0.12em;
    color: var(--bone-faint);
    margin-top: 0.45rem;
    text-transform: uppercase;
}}

/*  verdict chip */
.mt-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--font-mono);
    font-size: 0.66rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 0.22rem 0.6rem;
    border-radius: 2px;
    border: 1px solid var(--chip, var(--lila));
    color: var(--chip, var(--lila));
}}
.mt-chip::before {{
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--chip, var(--lila));
    box-shadow: 0 0 8px var(--chip, var(--lila));
}}

/*  sidebar */
[data-testid="stSidebar"] {{
    background:
        linear-gradient(180deg, rgba(176,127,255,0.05), transparent 30%),
        var(--panel) !important;
    border-right: 1px solid var(--line) !important;
}}
[data-testid="stSidebar"] button {{
    font-family: var(--font-mono) !important;
    letter-spacing: 0.09em !important;
    color: var(--bone) !important;
    border: 1px solid transparent !important;
    border-left: 2px solid transparent !important;
    background: transparent !important;
    transition: all 0.15s ease !important;
    font-size: 0.8rem !important;
    text-align: left !important;
    border-radius: 0 !important;
}}
[data-testid="stSidebar"] button:hover {{
    border-color: var(--lila-dim) !important;
    border-left: 2px solid var(--lila) !important;
    color: var(--lila-bright) !important;
    background: var(--panel2) !important;
}}
.nav-active button {{
    background: var(--panel2) !important;
    border-left: 2px solid var(--amber) !important;
    border-color: var(--line) !important;
    color: var(--amber) !important;
    text-shadow: 0 0 8px var(--yellow-glow) !important;
}}

/*  generic buttons */
.stButton button, button[kind] {{
    font-family: var(--font-mono) !important;
    letter-spacing: 0.12em !important;
    color: var(--bone) !important;
    border: 1px solid var(--line) !important;
    background: var(--panel) !important;
    border-radius: 2px !important;
    transition: all 0.15s ease !important;
    text-transform: uppercase !important;
    font-size: 0.78rem !important;
}}
.stButton button:hover, button[kind]:hover {{
    border-color: var(--lila) !important;
    color: var(--lila-bright) !important;
    box-shadow: 0 0 0 1px var(--lila-glow), 0 0 16px rgba(176,127,255,0.18) !important;
}}
.stButton button[kind="primary"] {{
    background: linear-gradient(180deg, var(--lila), var(--lila-dim)) !important;
    color: var(--void) !important;
    border-color: var(--lila) !important;
    font-weight: 600 !important;
}}
.stButton button[kind="primary"]:hover {{
    background: linear-gradient(180deg, var(--lila-bright), var(--lila)) !important;
    box-shadow: 0 0 22px var(--lila-glow) !important;
}}

/*  inputs */
[data-testid="stSelectbox"] > div, [data-baseweb="select"] > div {{
    background: var(--panel) !important;
    border-color: var(--line) !important;
    border-radius: 2px !important;
    font-family: var(--font-mono) !important;
}}
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {{
    background: var(--void) !important;
    border: 1px solid var(--line) !important;
    color: var(--bone) !important;
    font-family: var(--font-mono) !important;
    border-radius: 2px !important;
}}
[data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus {{
    border-color: var(--lila) !important;
    box-shadow: 0 0 0 1px var(--lila-glow) !important;
}}
[data-testid="stWidgetLabel"] label, .stSelectbox label, .stSlider label {{
    font-family: var(--font-mono) !important;
    font-size: 0.64rem !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: var(--lila-bright) !important;
}}

/* Slider accents */
[data-testid="stSlider"] [role="slider"] {{ background: var(--amber) !important; }}
[data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {{
    background: var(--lila) !important;
}}

/*  captions etc */
[data-testid="stCaptionContainer"], .stCaption, small {{
    font-family: var(--font-mono) !important;
    font-size: 0.62rem !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: var(--lila-bright) !important;
    opacity: 0.78;
}}

/*  expanders */
/* Evidence-docket framing. Plain-text labels keep Streamlit from escaping. */
[data-testid="stExpander"] {{
    border: 1px solid var(--line) !important;
    background:
        linear-gradient(180deg, rgba(176,127,255,0.03), transparent 30%),
        var(--panel) !important;
    border-radius: 2px !important;
    position: relative !important;
    overflow: hidden !important;
    margin-bottom: 0.55rem !important;
}}
[data-testid="stExpander"]::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 2px;
    background: var(--lila-dim);
}}
[data-testid="stExpander"]:hover {{ border-color: var(--lila-dim) !important; }}
[data-testid="stExpander"] summary {{
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em !important;
    color: var(--bone) !important;
}}
[data-testid="stExpander"] summary:hover {{ color: var(--lila-bright) !important; }}

/*  code blocks */
code, pre, [data-testid="stCode"] {{
    font-family: var(--font-mono) !important;
    background: var(--void) !important;
    color: var(--lila-bright) !important;
    border: 1px solid var(--line) !important;
    font-size: 0.76rem !important;
    border-radius: 2px !important;
}}

/* info / alerts */
[data-testid="stAlert"] {{
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-left: 3px solid var(--lila) !important;
    border-radius: 2px !important;
    font-family: var(--font-mono) !important;
}}

hr {{
    border: none !important;
    border-top: 1px solid var(--line) !important;
    margin: 1.4rem 0 !important;
}}

/*  pulse + dots */
@keyframes pulse-lila {{
    0%   {{ box-shadow: 0 0 0 0 var(--mint); opacity: 1; }}
    70%  {{ box-shadow: 0 0 0 7px rgba(61,245,192,0); opacity: 0.7; }}
    100% {{ box-shadow: 0 0 0 0 rgba(61,245,192,0); opacity: 1; }}
}}
.pulse-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--mint);
    animation: pulse-lila 2.2s ease-in-out infinite;
    vertical-align: middle;
    margin-right: 6px;
}}

/*  hero rail */
.mt-hero {{
    position: relative;
    border: 1px solid var(--line);
    border-radius: 2px;
    background:
        linear-gradient(120deg, rgba(176,127,255,0.10), transparent 55%),
        var(--panel);
    padding: 1.5rem 1.7rem;
    margin-bottom: 1.6rem;
    overflow: hidden;
}}
.mt-hero::after {{
    content: '';
    position: absolute;
    top: 0; left: -40%;
    width: 40%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(217,184,255,0.12), transparent);
    animation: mt-sweep 6s ease-in-out infinite;
}}
@keyframes mt-sweep {{
    0%   {{ left: -40%; }}
    55%  {{ left: 130%; }}
    100% {{ left: 130%; }}
}}
.mt-hero-eyebrow {{
    font-family: var(--font-mono);
    font-size: 0.62rem;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--lila-bright);
}}
.mt-hero-title {{
    font-family: var(--font-head);
    font-size: 2.0rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    color: var(--bone);
    margin: 0.35rem 0 0.2rem;
    text-transform: uppercase;
}}
.mt-hero-title em {{ font-style: normal; color: var(--amber); }}
.mt-hero-sub {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    color: var(--bone-dim);
}}

/*  scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: var(--void); }}
::-webkit-scrollbar-thumb {{ background: var(--lila-dim); border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--lila); }}

/*  reduced motion */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation: none !important;
        transition: none !important;
    }}
}}

/*  responsive */
@media (max-width: 820px) {{
    .block-container {{ padding: 1.2rem 1rem 3rem !important; }}
    .mt-hero-title {{ font-size: 1.5rem; }}
    .mt-cell .mt-value {{ font-size: 1.8rem; }}
}}
"""


def inject() -> None:
    """Injects the base stylesheet. Must be called once per page, before content."""
    css = _BASE_CSS.format(
        font_head=FONTS["head"],
        font_mono=FONTS["mono"],
        font_body=FONTS["body"],
        **COLORS,
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def section_header(icon: str, title: str, sub: str = "") -> None:
    """Renders a framed section header with a meaning-bearing accent rail."""
    sub_html = f'<span class="section-header-sub">{sub}</span>' if sub else ""
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-header-icon">{icon}</span>'
        f'<span class="section-header-title">{title}</span>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def hero(eyebrow: str, title_html: str, sub: str = "") -> None:
    """Renders the page hero rail. `title_html` may contain <em> for the amber accent."""
    sub_html = f'<div class="mt-hero-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="mt-hero">'
        f'<div class="mt-hero-eyebrow">{eyebrow}</div>'
        f'<div class="mt-hero-title">{title_html}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def metric_console(items) -> None:
    """
    Renders a row of forensic instrument readouts.

    `items`: list of dicts with keys:
        label  (str)  — uppercase micro-label
        value  (str)  — the headline value
        accent (str)  — one of: lila, amber, rose, mint, ice  (default amber)
        sub    (str)  — optional small caption under the value
    """
    accent_map = {
        "lila":  "var(--lila-bright)",
        "amber": "var(--amber)",
        "rose":  "var(--rose)",
        "mint":  "var(--mint)",
        "ice":   "var(--ice)",
    }
    cells = []
    for it in items:
        accent = accent_map.get(it.get("accent", "amber"), "var(--amber)")
        sub = f'<div class="mt-sub">{it["sub"]}</div>' if it.get("sub") else ""
        cells.append(
            f'<div class="mt-cell" style="--accent:{accent};">'
            f'<div class="mt-label">{it["label"]}</div>'
            f'<div class="mt-value">{it["value"]}</div>'
            f'{sub}'
            f'</div>'
        )
    st.markdown(f'<div class="mt-console">{"".join(cells)}</div>', unsafe_allow_html=True)


def verdict_chip(verdict: str) -> str:
    """Returns an inline HTML chip string for a verdict (embeddable in markdown)."""
    color, label = _VERDICT_META.get(verdict, ("var(--lila)", verdict))
    return f'<span class="mt-chip" style="--chip:{color};">{label}</span>'


def force_sidebar_open() -> None:
    """
    Intentionally a no-op.

    Forcing the collapsed-control open was found to push the sidebar into an
    unrecoverable state on rerun. The sidebar is already configured to start
    expanded via st.set_page_config(initial_sidebar_state="expanded").
    """
    pass
