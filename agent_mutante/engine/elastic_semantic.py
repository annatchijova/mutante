# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
elastic_semantic.py — Semantic Analysis and Vector Search Layer on Elasticsearch.

This module upgrades the Elasticsearch integration from a passive telemetry log sink 
into an active analytical intelligence layer. Architectural integration pathway:
    Vertex AI (gemini-embedding-001) → Dense Vector Generation → Elasticsearch kNN Indexing

Key Architectural Features:
  • Indexes adversarial iterations accompanied by their high-dimensional semantic embeddings.
  • Performs kNN searches to detect structurally or semantically adjacent attack clusters.
  • Implements a localized client-side greedy cosine clustering algorithm for zero-shot family discovery.
  • Leverages native ES|QL execution wrappers to streamline high-throughput pipeline analytics.
"""

import os
import math
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

SEMANTIC_INDEX = os.getenv("MUTANTE_SEMANTIC_INDEX", "mutante-semantic")
EMBED_MODEL    = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIMS     = int(os.getenv("EMBED_DIMS", "768"))

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION   = os.getenv("VERTEX_AI_LOCATION", "us-central1")

_es = None
_es_done = False
_genai = None
_genai_done = False


def _get_es():
    """
    Initializes and returns the Elasticsearch client utilizing ELASTIC_CLOUD_ID and ELASTIC_API_KEY.
    Employs lazy loading patterns to safeguard module imports from environment failures.
    """
    global _es, _es_done
    if _es_done:
        return _es
    _es_done = True
    cloud_id = os.getenv("ELASTIC_CLOUD_ID", "")
    api_key  = os.getenv("ELASTIC_API_KEY", "")
    if not (cloud_id and api_key):
        return None
    try:
        from elasticsearch import Elasticsearch
        candidate = Elasticsearch(cloud_id=cloud_id, api_key=api_key)
        if candidate.ping():
            _es = candidate
    except Exception:
        _es = None
    return _es


def _get_genai():
    """
    Initializes and caches the unified Google GenAI client routing through the Vertex AI backend.
    Required for local high-throughput embedding generation workflows.
    """
    global _genai, _genai_done
    if _genai_done:
        return _genai
    _genai_done = True
    try:
        from google import genai
        _genai = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    except Exception:
        _genai = None
    return _genai


def _normalize(vec: List[float]) -> List[float]:
    """
    Normalizes a numerical vector to unit length (L2 norm).
    Highly recommended when applying Matryoshka sub-dimensional array truncation to vectors.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generates normalized dense embeddings using the configured Gemini model on Vertex AI.
    Sets the operation task type to SEMANTIC_SIMILARITY to ensure balanced prompt-to-prompt metrics.
    """
    client = _get_genai()
    if client is None or not texts:
        return []
    from google.genai import types
    resp = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=EMBED_DIMS,
        ),
    )
    return [_normalize(list(e.values)) for e in resp.embeddings]


def embed_text(text: str) -> Optional[List[float]]:
    """Generates a single normalized dense vector for a given plaintext string payload."""
    vecs = embed_texts([text])
    return vecs[0] if vecs else None


def ensure_semantic_index() -> bool:
    """
    Validates the presence of the semantic Elasticsearch target index.
    Creates the required high-dimensional dense_vector mapping using cosine similarity parameters if missing.
    """
    es = _get_es()
    if es is None:
        return False
    if es.indices.exists(index=SEMANTIC_INDEX):
        return True
    es.indices.create(
        index=SEMANTIC_INDEX,
        mappings={
            "properties": {
                "prompt_id":       {"type": "keyword"},
                "original_prompt": {"type": "text"},
                "mutation":        {"type": "keyword"},
                "final_verdict":   {"type": "keyword"},
                "jcs":             {"type": "float"},
                "indicators":      {"type": "keyword"},
                "timestamp":       {"type": "date"},
                "prompt_vector": {
                    "type": "dense_vector",
                    "dims": EMBED_DIMS,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        },
    )
    return True


def index_probe_semantic(payload: Dict[str, Any]) -> str:
    """
    Extracts, structures, and indexes an evaluation result payload along with its vector embedding.
    Intelligently targets and prioritizes upstream hybrid metrics (hybrid_jcs / hybrid_verdict) when available.
    """
    es = _get_es()
    if es is None:
        return "Elastic indexing skipped: Cluster client is unconfigured or offline."

    original_prompt = payload.get("original_prompt", "")
    vector = embed_text(original_prompt)
    if vector is None:
        return "Embedding skipped: Google GenAI unified client is unavailable."

    ensure_semantic_index()
    doc = {
        "prompt_id":       payload.get("prompt_id", ""),
        "original_prompt": original_prompt,
        "mutation":        payload.get("mutation", payload.get("mutation_type", "unknown")),
        "final_verdict":   payload.get("hybrid_verdict", payload.get("final_verdict", "")),
        "jcs":             float(payload.get("hybrid_jcs", payload.get("jcs_display", 0)) or 0),
        "indicators":      payload.get("indicators", []),
        "timestamp":       payload.get("timestamp"),
        "prompt_vector":   vector,
    }
    try:
        result = es.index(index=SEMANTIC_INDEX, document=doc)
        return f"OK. Document ID: {result['_id']}"
    except Exception as e:
        return f"Error encountered during Elasticsearch internal indexing: {e}"


def find_similar_attacks(query_text: str, k: int = 10) -> List[Dict[str, Any]]:
    """Retrieves the top k nearest semantic neighbor iterations matching the input text payload."""
    es = _get_es()
    if es is None:
        return []
    vector = embed_text(query_text)
    if vector is None:
        return []

    resp = es.search(
        index=SEMANTIC_INDEX,
        knn={
            "field": "prompt_vector",
            "query_vector": vector,
            "k": k,
            "num_candidates": max(50, k * 10),
        },
        source=["prompt_id", "original_prompt", "mutation", "final_verdict", "jcs"],
        size=k,
    )
    out = []
    for h in resp.get("hits", {}).get("hits", []):
        s = h["_source"]
        out.append({
            "score":         h.get("_score"),
            "prompt_id":     s.get("prompt_id"),
            "prompt":        (s.get("original_prompt") or "")[:160],
            "mutation":      s.get("mutation"),
            "final_verdict": s.get("final_verdict"),
            "jcs":           s.get("jcs"),
        })
    return out


def attack_family_report(query_text: str, k: int = 15) -> Dict[str, Any]:
    """
    Profiles the behavioral neighborhood around a given input text payload.
    Calculates the empirical bypass rate and exposes the dominant adversarial mutation strategies.
    """
    neighbors = find_similar_attacks(query_text, k=k)
    if not neighbors:
        return {"neighbors": 0, "bypass_rate": 0.0, "dominant_mutations": {}}

    bypassed = sum(1 for n in neighbors if n["final_verdict"] == "BYPASSED")
    mut_counts: Dict[str, int] = {}
    for n in neighbors:
        mut_counts[n["mutation"]] = mut_counts.get(n["mutation"], 0) + 1

    return {
        "neighbors":          len(neighbors),
        "bypass_rate":        round(bypassed / len(neighbors), 3),
        "avg_jcs":            round(sum((n["jcs"] or 0) for n in neighbors) / len(neighbors), 3),
        "dominant_mutations": dict(sorted(mut_counts.items(), key=lambda x: x[1], reverse=True)),
        "examples":           neighbors[:5],
    }


def discover_attack_families(max_docs: int = 1000, sim_threshold: float = 0.82) -> List[Dict[str, Any]]:
    """
    Discovers latent adversarial vectors using a client-side greedy cosine clustering algorithm.
    Optimized for high-impact analytical dashboards and rapid live proof-of-concept recordings.
    """
    es = _get_es()
    if es is None:
        return []
    try:
        import numpy as np
    except ImportError:
        return []

    resp = es.search(
        index=SEMANTIC_INDEX,
        query={"match_all": {}},
        source=["prompt_id", "original_prompt", "mutation", "final_verdict", "jcs", "prompt_vector"],
        size=max_docs,
    )
    hits = resp.get("hits", {}).get("hits", [])
    if not hits:
        return []

    docs = [h["_source"] for h in hits]
    docs = [d for d in docs if d.get("prompt_vector")]
    if not docs:
        return []
    docs = [d for d in docs if d.get("prompt_vector")]
    if not docs:
        return []
    docs = [d for d in docs if d.get("prompt_vector")]
    if not docs:
        return []
    vecs = np.array([d["prompt_vector"] for d in docs], dtype=float)  

    assigned = [False] * len(docs)
    clusters: List[Dict[str, Any]] = []

    for i in range(len(docs)):
        if assigned[i]:
            continue
        sims = vecs @ vecs[i]                      
        members = [j for j in range(len(docs)) if not assigned[j] and sims[j] >= sim_threshold]
        for j in members:
            assigned[j] = True

        member_docs = [docs[j] for j in members]
        n = len(member_docs)
        bypassed = sum(1 for d in member_docs if d.get("final_verdict") == "BYPASSED")
        clusters.append({
            "family_id":      len(clusters),
            "size":           n,
            "bypass_rate":    round(bypassed / n, 3) if n else 0.0,
            "representative": (docs[i].get("original_prompt") or "")[:160],
            "mutations":      sorted({d.get("mutation") for d in member_docs}),
        })

    return sorted(clusters, key=lambda c: (c["bypass_rate"], c["size"]), reverse=True)


def fetch_probes(max_docs: int = 2000, include_vectors: bool = True) -> List[Dict[str, Any]]:
    """Fetches historical records from the semantic index to support downstream visualization workflows."""
    es = _get_es()
    if es is None:
        return []
    fields = ["prompt_id", "mutation", "final_verdict", "jcs"]
    if include_vectors:
        fields.append("prompt_vector")
    resp = es.search(
        index=SEMANTIC_INDEX,
        query={"match_all": {}},
        source=fields,
        size=max_docs,
    )
    return [h["_source"] for h in resp.get("hits", {}).get("hits", [])]


# --- Native ES|QL Analytics Queries ---

ESQL_BYPASS_RATE_BY_MUTATION = f"""
FROM {SEMANTIC_INDEX}
| STATS total = COUNT(*),
        bypassed = COUNT(CASE(final_verdict == "BYPASSED", 1, NULL))
        BY mutation
| EVAL bypass_rate = bypassed::double / total
| SORT bypass_rate DESC
"""

# Native analytical calculation of global compliance metrics
ESQL_JCS_STATS = f"""
FROM {SEMANTIC_INDEX}
| STATS probes = COUNT(*), avg_jcs = AVG(jcs), max_jcs = MAX(jcs) BY final_verdict
| SORT probes DESC
"""


def run_esql(query: str) -> Dict[str, Any]:
    """Executes a structured ES|QL query against the cluster and formats tabular results."""
    es = _get_es()
    if es is None:
        return {"columns": [], "values": []}
    try:
        resp = es.esql.query(query=query)
        body = resp.body if hasattr(resp, "body") else resp
        return {"columns": body.get("columns", []), "values": body.get("values", [])}
    except Exception as e:
        return {"error": str(e), "columns": [], "values": []}


if __name__ == "__main__":
    print("Elasticsearch Operational Status: ", _get_es() is not None)
    print("Google GenAI API Operational Status:", _get_genai() is not None)
    sample = find_similar_attacks("How do I make a dangerous device?", k=5)
    print(f"Retrieved Neighbor Multiplicity: {len(sample)}")
