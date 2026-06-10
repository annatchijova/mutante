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
analytics.py — Real-Time Statistical Telemetry Driven by Native ES|QL.

PERFORMANCE OPTIMIZATION NOTE:
This component deprecates historical client-side Pandas data manipulation loops.
Aggregations and statistical distributions are executed directly inside the Elasticsearch 
cluster using native Elasticsearch Query Language (ES|QL), minimizing network payload
overhead and making the analytics sub-second and highly scale-invariant.
"""

import os
import streamlit as st
import plotly.graph_objects as go
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from components.css import section_header, hero, COLORS

load_dotenv()

AUDIT_INDEX = os.getenv("MUTANTE_AUDIT_INDEX", "mutante-semantic")

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Share Tech Mono", color=COLORS.get("text_dim", "#888")),
    margin=dict(l=50, r=20, t=30, b=40),
)

_AXIS_DEFAULTS = dict(
    showgrid=True,
    gridcolor=COLORS.get("border", "#333"),
    linecolor=COLORS.get("border", "#333"),
    tickfont=dict(family="Share Tech Mono", size=10),
)

# --- Native ES|QL Analytical Pipelines ---
ESQL_JCS_TIMELINE = f"""
FROM {AUDIT_INDEX}
| KEEP timestamp, jcs, final_verdict
| SORT timestamp ASC
"""

ESQL_MUTATION_PERFORMANCE = f"""
FROM {AUDIT_INDEX}
| STATS total = COUNT(*), bypassed = COUNT(CASE(final_verdict == "BYPASSED", 1, NULL)) BY mutation
| EVAL rate = (bypassed::double / total) * 100.0
| SORT rate DESC
"""


def _run_esql(query: str) -> dict:
    """Dispatches native ES|QL execution requests directly to the unmanaged cluster infrastructure."""
    cloud_id = os.getenv("ELASTIC_CLOUD_ID", "")
    api_key  = os.getenv("ELASTIC_API_KEY", "")
    if not (cloud_id and api_key):
        return {"columns": [], "values": []}
    try:
        es = Elasticsearch(cloud_id=cloud_id, api_key=api_key)
        resp = es.esql.query(query=query)
        return resp.body if hasattr(resp, "body") else resp
    except Exception as e:
        st.error(f"ES|QL Execution Failure: {e}")
        return {"columns": [], "values": []}


def _jcs_timeline_fig(data: dict) -> go.Figure:
    """Constructs chronological tracking charts mapping safety regression anomalies."""
    cols = [c["name"] for c in data["columns"]]
    vals = data["values"]

    i_time    = cols.index("timestamp")
    i_jcs     = cols.index("jcs")
    i_verdict = cols.index("final_verdict")

    times    = [v[i_time] for v in vals]
    jcs_vals = [v[i_jcs] for v in vals]
    verdicts = [v[i_verdict] for v in vals]

    colors = [
        COLORS.get("yellow", "#FFD700") if v == "BYPASSED" 
        else COLORS.get("lila_bright", "#BA55D3") if v == "UNCERTAIN" 
        else COLORS.get("text_dim", "#888") 
        for v in verdicts
    ]

    fig = go.Figure(go.Scatter(
        x=times, y=jcs_vals,
        mode="markers+lines",
        marker=dict(color=colors, size=6, symbol="square-open"),
        line=dict(color=COLORS.get("border", "#333"), width=1)
    ))

    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        height=280,
        xaxis=dict(**_AXIS_DEFAULTS, type="date"),
        yaxis=dict(**_AXIS_DEFAULTS, title="JCS SCORE MAPPING"),
    )
    return fig


def _mutation_bar_fig(data: dict) -> go.Figure:
    """Builds categorical distributions evaluating individual mutation vulnerability thresholds."""
    cols = [c["name"] for c in data["columns"]]
    vals = data["values"]

    i_mut  = cols.index("mutation")
    i_rate = cols.index("rate")

    mutations = [str(r[i_mut]) for r in vals]
    rates     = [float(r[i_rate]) if r[i_rate] is not None else 0.0 for r in vals]

    fig = go.Figure(go.Bar(x=mutations, y=rates, marker_color=COLORS.get("lila_bright", "#BA55D3")))
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        height=300,
        xaxis=dict(**_AXIS_DEFAULTS, title="TRANSFORMATION VECTOR"),
        yaxis=dict(**_AXIS_DEFAULTS, title="BYPASS RATE (%)", range=[0, 100]),
    )
    return fig


def render() -> None:
    """Orchestrates layout pipelines and renders the analytical data visualization workspace."""
    hero(
        "Statistical Telemetry · Native ES|QL",
        'ANALYTICS <em>ENGINE</em>',
        "Sub-second cluster-side aggregation · JCS regression tracking · vector vulnerability mapping",
    )
    timeline = _run_esql(ESQL_JCS_TIMELINE)

    if not timeline.get("values"):
        st.markdown(
            f'<div style="font-family:Share Tech Mono,monospace;color:{COLORS.get("yellow", "#FFD700")};'
            f'border:1px solid {COLORS.get("yellow", "#FFD700")};border-radius:2px;'
            f'padding:1rem 1.4rem;font-size:0.82rem;letter-spacing:0.1em;">'
            f'⚠ &nbsp; NO DATA — Run live agent iterations to populate the forensic index.</div>',
            unsafe_allow_html=True,
        )
        return

    section_header("◈", "JCS Timeline", "Continuous Jailbreak Confidence Tracking driven by native ES|QL analytics")
    st.plotly_chart(_jcs_timeline_fig(timeline), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("⬡", "Mutation Vector Analysis", "Vulnerability distribution mapped per adversarial semantic vector transformation")
    
    mutation_data = _run_esql(ESQL_MUTATION_PERFORMANCE)
    if mutation_data.get("values"):
        st.plotly_chart(_mutation_bar_fig(mutation_data), use_container_width=True, config={"displayModeBar": False})
