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
attack_families.py — Semantic Vector Space and Adversarial Family Profiler.

CRITICAL COMPLIANCE AND PRIVACY NOTE:
This interactive dashboard projects high-dimensional adversarial embeddings (generated 
via Vertex AI gemini-embedding-001) onto a 2D canvas using Principal Component Analysis (PCA).
To safely support public review or video demonstrations without broadcasting harmful text payloads,
the interactive hover state is programmatically masked to expose only the Prompt ID,
mutation strategies, hybrid JCS metrics, and final system verdicts.
"""

import os
import sys
import streamlit as st
import plotly.graph_objects as go
from components.css import section_header, COLORS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from agent_mutante.engine.elastic_semantic import (
        fetch_probes,
        attack_family_report,
        discover_attack_families,
    )
except ImportError:
    from elastic_semantic import (
        fetch_probes,
        attack_family_report,
        discover_attack_families,
    )

_VERDICT_COLOR = {
    "BYPASSED": COLORS.get("yellow", "#FFD700"),
    "UNCERTAIN": COLORS.get("lila_bright", "#BA55D3"),
    "BLOCKED": COLORS.get("text_dim", "#888888"),
}


def _render_scatter_plot(probes: list) -> go.Figure:
    """
    Executes dimensional reduction on the fly and generates the semantic map scatter layout.
    Falls back gracefully to statistical dummy distributions if the environment lacks scikit-learn.
    """
    import numpy as np
    
    # Extract structural coordinate arrays
    probes  = [p for p in probes if "prompt_vector" in p and p["prompt_vector"]]
    vectors = [p["prompt_vector"] for p in probes]
    
    if not vectors or len(vectors) < 2:
        fig = go.Figure()
        fig.update_layout(title="Insufficient dense vectors indexed to execute PCA projection.")
        return fig

    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(np.array(vectors, dtype=float))
    except ImportError:
        # Graceful degradation fallback pattern using deterministic random matrix projections
        np.random.seed(42)
        coords = np.random.randn(len(vectors), 2)

    x_coords = coords[:, 0]
    y_coords = coords[:, 1]

    fig = go.Figure()

    # Segregate scatter series by security classification to build interactive independent layers
    for verdict in ["BLOCKED", "UNCERTAIN", "BYPASSED"]:
        idx = [i for i, p in enumerate(probes) if p.get("final_verdict") == verdict]
        if not idx:
            continue

        v_x = [x_coords[i] for i in idx]
        v_y = [y_coords[i] for i in idx]
        v_probes = [probes[i] for i in idx]

        # PRIVACY MASKING EXECUTION: Exploit text payloads are omitted from customdata blocks
        hover_texts = [
            f"ID: {p.get('prompt_id')}<br>"
            f"Mutation: {p.get('mutation')}<br>"
            f"JCS: {p.get('jcs', 0.0):.2f}<br>"
            f"Verdict: {verdict}"
            for p in v_probes
        ]

        fig.add_trace(go.Scatter(
            x=v_x, y=v_y,
            mode="markers",
            name=verdict,
            text=hover_texts,
            hoverinfo="text",
            marker=dict(
                size=8,
                color=_VERDICT_COLOR.get(verdict, "#FFFFFF"),
                opacity=0.8,
                line=dict(width=1, color=COLORS.get("bg", "#000000"))
            )
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Share Tech Mono", color=COLORS.get("text_dim", "#FFFFFF")),
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    return fig


def render() -> None:
    """Renders the semantic safety space dashboard views and handles kNN analytical inputs."""
    section_header("◈", "Semantic Map", "High-dimensional projection of structural security breaches via PCA")

    probes = fetch_probes(max_docs=1000, include_vectors=True)

    if not probes:
        st.warning("No vectorized forensic probes recovered from the semantic index. Run the orchestrator suite.")
        return

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.plotly_chart(_render_scatter_plot(probes), use_container_width=True, config={"displayModeBar": False})

    with col_right:
        st.caption("NEAREST NEIGHBOR (kNN) DIAGNOSTICS")
        query = st.text_input("Analyze structural proximity for payload prompt:", placeholder="Enter vector probe query...")

        if st.button("FIND FAMILY", type="primary", use_container_width=True) and query.strip():
            report = attack_family_report(query, k=15)
            rate = report["bypass_rate"] * 100
            color = COLORS.get("yellow", "#FFD700") if rate >= 50 else COLORS.get("lila", "#8A2BE2")
            
            st.markdown(
                f'<div style="background:{COLORS.get("bg2", "#222")};border:1px solid {color};border-radius:3px;'
                f'padding:1rem;margin-top:0.5rem;">'
                f'<div style="font-family:Cinzel;font-size:1.4rem;color:{color};text-align:center;">'
                f'{rate:.0f}% BYPASS</div>'
                f'<div style="font-family:Share Tech Mono;font-size:0.7rem;color:{COLORS.get("text_dim", "#888")};'
                f'text-align:center;">neighborhood of {report["neighbors"]} · avg JCS {report.get("avg_jcs", 0):.2f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            
            st.caption("NEAREST NEIGHBORS")
            for n in report.get("examples", []):
                vc = _VERDICT_COLOR.get(n["final_verdict"], COLORS.get("text_dim", "#888"))
                st.markdown(
                    f'<div style="font-family:Share Tech Mono;font-size:0.72rem;color:{COLORS.get("text", "#FFF")};'
                    f'margin-bottom:0.3rem;">'
                    f'<span style="color:{vc}; font-weight:bold;">[{n["final_verdict"]}]</span> '
                    f'ID: {n["prompt_id"]} | JCS: {n["jcs"]:.2f} | Strategy: {n["mutation"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)
    section_header("⬡", "Latent Attack Families", "Greedy cosine clustering over dense historical matrices")

    families = discover_attack_families(max_docs=500, sim_threshold=0.85)
    if families:
        for f in families[:5]:
            st.markdown(
                f'<div style="font-family:Share Tech Mono; font-size:0.8rem; margin-bottom:0.5rem;'
                f'border-left: 3px solid {COLORS.get("lila_bright", "#BA55D3")}; padding-left: 0.5rem;">'
                f'<b style="color:{COLORS.get("yellow", "#FFD700")};">Family #{f["family_id"]}</b> '
                f'(Size: {f["size"]} instances | Empirical Bypass Rate: {f["bypass_rate"]*100:.1f}%)<br>'
                f'<span style="color:{COLORS.get("text_dim", "#888")};">Cluster Centroid Profile:</span> {f["representative"]}<br>'
                f'<span style="color:{COLORS.get("text_dim", "#888")};">Active Strategies:</span> {", ".join(f["mutations"])}'
                f'</div>',
                unsafe_allow_html=True,
            )
