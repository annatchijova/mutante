# Copyright 2026 Anna Tchijova
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

"""forensic_feed.py — Chronological log with THREAT CATEGORY badges."""

import os
import streamlit as st
import pandas as pd
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
                "size": 500,
                "sort": [{"_doc": {"order": "desc"}}],
            },
        )
    except Exception as e:
        st.error(f"Telemetry retrieval failed: {e}")
        return pd.DataFrame()

    rows = []
    for h in resp.get("hits", {}).get("hits", []):
        s = h["_source"]
        rows.append({
            "success": s.get("success", False),
            "final_verdict": "BYPASSED" if s.get("success") else "BLOCKED",
            "jcs": float(s.get("jcs_display", s.get("jcs", 0)) or 0),
            "mutation": s.get("mutation", "unknown"),
            "category": s.get("category", "unknown"),
            "indicators": s.get("indicators", []),
            "original_prompt": s.get("original_prompt", ""),
            "mutated_prompt": s.get("mutated_prompt", ""),
            "response": s.get("raw_response", ""),
        })
    return pd.DataFrame(rows)

def _category_badge(category: str) -> str:
    color_map = {
        "organic": COLORS["lila"],
        "copyright": COLORS["yellow"],
        "illegal": COLORS["red"],
        "misinformation_disinformation": COLORS["cyan"],
        "cybercrime_intrusion": COLORS["green"],
        "chemical_biological": "#FF8800",
        "harassment_bullying": "#FF44AA",
        "harmful": COLORS["red"],
    }
    color = color_map.get(category, COLORS["text_dim"])
    return f'<span style="display:inline-block;font-family:Share Tech Mono;font-size:0.65rem;' \
           f'color:{color};border:1px solid {color};border-radius:2px;' \
           f'padding:0.1rem 0.4rem;margin-left:0.5rem;letter-spacing:0.05em;">' \
           f'{category.upper()}</span>'

def render() -> None:
    df = fetch()
    section_header("⬡", "Forensic Feed", "Immutable telemetry log with threat categorization")

    if df.empty:
        st.info("The forensic index is empty or Elastic Cloud is unreachable.")
        return

    c1, c2, c3, c4 = st.columns(4)
    verdict_filter = c1.selectbox("VERDICT", ["ALL", "BYPASSED", "BLOCKED"], key="ff_verd")
    
    muts = ["ALL"] + sorted(df["mutation"].unique().tolist())
    mut_filter = c2.selectbox("VECTOR", muts, key="ff_mut")
    
    cats = ["ALL"] + sorted(df["category"].unique().tolist())
    cat_filter = c3.selectbox("CATEGORY", cats, key="ff_cat")
    
    jcs_threshold = c4.slider("MIN JCS", min_value=0.0, max_value=float(df["jcs"].max() or 2.0), value=0.0, step=0.1, key="ff_jcs")

    st.markdown("<hr/>", unsafe_allow_html=True)

    filtered = df.copy()
    if verdict_filter != "ALL":
        filtered = filtered[filtered["final_verdict"] == verdict_filter]
    if mut_filter != "ALL":
        filtered = filtered[filtered["mutation"] == mut_filter]
    if cat_filter != "ALL":
        filtered = filtered[filtered["category"] == cat_filter]
    filtered = filtered[filtered["jcs"] >= jcs_threshold]

    st.caption(f"Showing {len(filtered)} filtered events")

    for idx, row in filtered.iterrows():
        # Circulo de color: amarillo dorado para BYPASSED, lila para BLOCKED
        if row["success"]:
            circle = "🟡"
            verdict_color = "#FFD700"
        else:
            circle = "🟣"
            verdict_color = "#8A7AAA"
        
        cat_badge = _category_badge(row["category"])
        
        # Titulo del expander en texto plano (sin HTML)
        expander_title = f"{circle} [{row['mutation'].upper()}] JCS: {row['jcs']:.2f} | {row['final_verdict']} | {row['category'].upper()}"
        
        with st.expander(expander_title):
            # Badge de categoria renderizado
            st.markdown(cat_badge, unsafe_allow_html=True)
            
            # Veredicto en color
            st.markdown(f'<div style="color:{verdict_color};font-family:Share Tech Mono;font-size:1.1rem;margin:0.5rem 0;">'
                       f'<strong>EVALUATOR VERDICT: {row["final_verdict"]}</strong></div>', 
                       unsafe_allow_html=True)
            
            if row["indicators"]:
                st.caption("SEMIOTIC INDICATORS")
                for ind in row["indicators"]:
                    st.markdown(f"- `{ind}`")

            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("ORIGINAL PROMPT")
                st.code(row["original_prompt"][:500], language=None)
            with col_b:
                st.caption("MUTATED PAYLOAD")
                st.code(row["mutated_prompt"][:500], language=None)

            if row["response"]:
                st.caption("AGENT RESPONSE (TRUNCATED)")
                st.code(row["response"][:400], language=None)
