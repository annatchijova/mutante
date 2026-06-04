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
command_center.py — Real-time operational summary.
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from components.css import section_header, COLORS

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
    except Exception as e:
        st.error(f"Elasticsearch connection error: {e}")
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
    if df.empty:
        return go.Figure()

    latest = df.iloc[0]
    fig = go.Figure(data=go.Scatterpolar(
        r=[latest["bsv_syntax"], latest["bsv_semantic"], latest["bsv_pragmatic"]],
        theta=["Syntax", "Semantic", "Pragmatic"],
        fill='toself',
        fillcolor=COLORS["lila_glow"],
        line=dict(color=COLORS["lila"]),
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=COLORS["border"], tickfont=dict(color=COLORS["text_dim"])),
            angularaxis=dict(tickfont=dict(color=COLORS["text_dim"], family="Share Tech Mono"), linecolor=COLORS["border"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=20),
        height=250,
    )
    return fig

def render() -> None:
    df = fetch()

    if st.button("⟳ Refresh", key="cc_refresh"):
        st.cache_data.clear()
        st.rerun()

    total = len(df)
    bypassed = int(df["success"].sum()) if not df.empty else 0
    blocked = total - bypassed
    rate = (bypassed / total * 100) if total else 0
    avg_jcs = df["jcs"].mean() if not df.empty else 0.0

    section_header("◈", "Operational Summary", f"{total} probes indexed")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("TOTAL PROBES", total)
    c2.metric("BYPASSED", bypassed)
    c3.metric("BLOCKED", blocked)
    c4.metric("BYPASS RATE", f"{rate:.1f}%")
    c5.metric("AVG JCS", f"{avg_jcs:.2f}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    section_header("◉", "Forensic Signal Analysis")
    col_radar, col_bandit, col_status = st.columns([1.1, 1.3, 0.9])

    with col_radar:
        st.caption("BSV — BYPASS SIGNAL VECTOR")
        st.plotly_chart(_render_radar(df), use_container_width=True, config={"displayModeBar": False})

    with col_bandit:
        st.caption("BAYESIAN BANDIT PROBABILITIES")
        if not df.empty and isinstance(df.iloc[0]["probs"], dict):
            probs = df.iloc[0]["probs"]
            for mut, p in sorted(probs.items(), key=lambda x: x[1], reverse=True):
                st.markdown(
                    f'<div style="margin-bottom:0.8rem;">'
                    f'<div style="display:flex;justify-content:space-between;font-family:Share Tech Mono;font-size:0.75rem;margin-bottom:0.2rem;">'
                    f'<span style="color:{COLORS["text"]};">{mut.upper()}</span>'
                    f'<span style="color:{COLORS["yellow"]};">{p*100:.1f}%</span>'
                    f'</div>'
                    f'<div style="width:100%;background-color:{COLORS["bg3"]};height:4px;border-radius:2px;">'
                    f'<div style="width:{p*100}%;background-color:{COLORS["lila"]};height:100%;border-radius:2px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("No probability data available.")

    with col_status:
        st.caption("SYSTEM STATUS")
        st.markdown(f'<div style="font-family:Share Tech Mono;margin-top:1rem;line-height:2;"><span class="pulse-dot"></span><span style="color:{COLORS["text"]};">MUTANTE ENGINE</span> <span style="color:{COLORS["green"]};">ONLINE</span><br><span class="pulse-dot"></span><span style="color:{COLORS["text"]};">ELASTIC SINK</span> <span style="color:{COLORS["green"]};">CONNECTED</span><br><span class="pulse-dot"></span><span style="color:{COLORS["text"]};">BIGQUERY SINK</span> <span style="color:{COLORS["text_dim"]};">STANDBY</span></div>', unsafe_allow_html=True)
