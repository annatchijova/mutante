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
command_center.py — Real-time operational summary, rendered as a forensic console.
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from components.css import section_header, hero, metric_console, COLORS

load_dotenv()


@st.cache_resource(ttl=0)
def _es():
    return Elasticsearch(
        cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
        api_key=os.getenv("ELASTIC_API_KEY"),
    )


@st.cache_data(ttl=15)
def fetch() -> pd.DataFrame:
    try:
        client = _es()
        if not client.ping():
            return pd.DataFrame()

        resp = client.search(
            index="mutante-audits",
            body={
                "query": {"match_all": {}},
                "size": 1000,
                "sort": [{"_doc": {"order": "desc"}}],
            },
        )
    except Exception:
        # Surfaced as a styled "no signal" state by the renderer, not a raw trace.
        return pd.DataFrame()

    rows = []
    for h in resp.get("hits", {}).get("hits", []):
        s = h["_source"]
        bsv = s.get("bsv", {})
        probs = s.get("probs", {})

        rows.append({
            "id": h["_id"],
            "success": s.get("success", False),
            "jcs": float(s.get("jcs_display", s.get("jcs", 0)) or 0),
            "mutation": s.get("mutation", "unknown"),
            "indicators": len(s.get("indicators", [])),
            "bsv_syntax": bsv.get("syntax", 0.0),
            "bsv_semantic": bsv.get("semantic", 0.0),
            "bsv_pragmatic": bsv.get("pragmatic", 0.0),
            "probs": probs,
        })
    return pd.DataFrame(rows)


def _render_radar(df: pd.DataFrame) -> go.Figure:
    """The Bypass Signal Vector, drawn as a three-axis signal scope."""
    if df.empty:
        return go.Figure()

    latest = df.iloc[0]
    fig = go.Figure(data=go.Scatterpolar(
        r=[latest["bsv_syntax"], latest["bsv_semantic"], latest["bsv_pragmatic"]],
        theta=["SYNTAX", "SEMANTIC", "PRAGMATIC"],
        fill="toself",
        fillcolor="rgba(176,127,255,0.22)",
        line=dict(color=COLORS["lila_bright"], width=2),
        marker=dict(color=COLORS["amber"], size=7, symbol="diamond"),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 1],
                gridcolor=COLORS["line"], linecolor=COLORS["line"],
                tickfont=dict(color=COLORS["bone_faint"], size=9, family="Share Tech Mono"),
                tickvals=[0.25, 0.5, 0.75, 1.0],
            ),
            angularaxis=dict(
                tickfont=dict(color=COLORS["lila_bright"], size=11, family="Share Tech Mono"),
                linecolor=COLORS["line"], gridcolor=COLORS["line"],
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=46, r=46, t=24, b=24),
        height=260,
        showlegend=False,
    )
    return fig


def _no_signal() -> None:
    """An intentional, on-brand empty state instead of a raw connection error."""
    st.markdown(
        f'<div style="border:1px solid {COLORS["line"]};border-left:3px solid {COLORS["amber"]};'
        f'background:{COLORS["panel"]};border-radius:2px;padding:1.6rem 1.8rem;margin-top:0.6rem;">'
        f'<div style="font-family:Share Tech Mono;font-size:0.62rem;letter-spacing:0.24em;'
        f'color:{COLORS["amber"]};text-transform:uppercase;">No signal · forensic index empty</div>'
        f'<div style="font-family:Rajdhani;font-size:1.05rem;color:{COLORS["bone"]};margin-top:0.5rem;'
        f'font-weight:300;line-height:1.5;">The audit index returned no probes, or Elastic Cloud is '
        f'unreachable. Repopulate with <span style="font-family:Share Tech Mono;color:{COLORS["lila_bright"]};">'
        f'python reseed_elastic.py --wipe</span> or run a live orchestrator batch.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    df = fetch()

    hero(
        "Operational Telemetry · Live",
        'COMMAND <em>CENTER</em>',
        "Adversarial probe stream · deterministic semiotic verdicts · Bayesian vector selection",
    )

    col_a, col_b = st.columns([0.18, 0.82])
    with col_a:
        if st.button("⟳ REFRESH", key="cc_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if df.empty:
        _no_signal()
        return

    total = len(df)
    bypassed = int(df["success"].sum())
    blocked = total - bypassed
    rate = (bypassed / total * 100) if total else 0
    avg_jcs = df["jcs"].mean() if not df.empty else 0.0

    section_header("◈", "Operational Summary", f"{total} probes indexed")

    metric_console([
        {"label": "Total Probes", "value": f"{total:,}", "accent": "lila",
         "sub": "indexed audits"},
        {"label": "Bypassed", "value": f"{bypassed}", "accent": "amber",
         "sub": "signal detected"},
        {"label": "Blocked", "value": f"{blocked}", "accent": "mint",
         "sub": "resisted"},
        {"label": "Bypass Rate", "value": f"{rate:.2f}%",
         "accent": "rose" if rate >= 10 else "amber",
         "sub": "of total surface"},
        {"label": "Avg JCS", "value": f"{avg_jcs:.2f}", "accent": "lila",
         "sub": "0–5 confidence"},
    ])

    st.markdown("<hr/>", unsafe_allow_html=True)

    section_header("◉", "Forensic Signal Analysis", "BSV · bandit posterior · subsystems")
    col_radar, col_bandit, col_status = st.columns([1.1, 1.3, 0.9])

    with col_radar:
        st.caption("BSV — Bypass Signal Vector")
        st.plotly_chart(_render_radar(df), use_container_width=True, config={"displayModeBar": False})

    with col_bandit:
        st.caption("Bayesian Bandit Posterior")
        if not df.empty and isinstance(df.iloc[0]["probs"], dict) and df.iloc[0]["probs"]:
            probs = df.iloc[0]["probs"]
            top = max(probs.items(), key=lambda x: x[1])[0]
            for mut, p in sorted(probs.items(), key=lambda x: x[1], reverse=True):
                bar_color = COLORS["amber"] if mut == top else COLORS["lila"]
                st.markdown(
                    f'<div style="margin-bottom:0.75rem;">'
                    f'<div style="display:flex;justify-content:space-between;font-family:Share Tech Mono;'
                    f'font-size:0.72rem;margin-bottom:0.25rem;">'
                    f'<span style="color:{COLORS["bone"]};letter-spacing:0.06em;">{mut.upper()}</span>'
                    f'<span style="color:{bar_color};">{p*100:.1f}%</span>'
                    f'</div>'
                    f'<div style="width:100%;background:{COLORS["void"]};height:5px;border-radius:2px;'
                    f'border:1px solid {COLORS["line"]};overflow:hidden;">'
                    f'<div style="width:{p*100:.1f}%;background:linear-gradient(90deg,{bar_color},'
                    f'{COLORS["lila_dim"]});height:100%;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No posterior data on the latest probe.")

    with col_status:
        st.caption("Subsystem Status")
        st.markdown(
            f'<div style="font-family:Share Tech Mono;margin-top:0.7rem;line-height:2.1;font-size:0.78rem;">'
            f'<span class="pulse-dot"></span><span style="color:{COLORS["bone"]};">MUTANTE ENGINE</span> '
            f'<span style="color:{COLORS["mint"]};float:right;">ONLINE</span><br>'
            f'<span class="pulse-dot"></span><span style="color:{COLORS["bone"]};">ELASTIC SINK</span> '
            f'<span style="color:{COLORS["mint"]};float:right;">CONNECTED</span><br>'
            f'<span class="pulse-dot"></span><span style="color:{COLORS["bone"]};">VERTEX AI</span> '
            f'<span style="color:{COLORS["mint"]};float:right;">READY</span><br>'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{COLORS["bone_faint"]};margin-right:6px;vertical-align:middle;"></span>'
            f'<span style="color:{COLORS["bone"]};">BIGQUERY SINK</span> '
            f'<span style="color:{COLORS["bone_dim"]};float:right;">STANDBY</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
