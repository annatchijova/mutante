#!/usr/bin/env python3
"""
reimport_semantic.py
Reconstructs the mutante-semantic Elasticsearch index from local JSONL audit files.

Usage:
    python3 reimport_semantic.py

Handles both batch_results.jsonl and demo_data.jsonl field schemas.
Records without prompt_vector are indexed normally — the PCA scatter plot
will activate its graceful fallback (random projection) when vectors are absent.
"""

import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from elasticsearch import Elasticsearch
from agent_mutante.engine.elastic_semantic import ensure_semantic_index, SEMANTIC_INDEX


def _es() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
        api_key=os.getenv("ELASTIC_API_KEY"),
    )


def _parse_jcs(row: dict) -> float:
    """
    Handles both numeric jcs and the fractional string format ('0/1', '1/3', etc.)
    used by the VIGÍA scoring engine. Falls back to jcs_display if parsing fails.
    """
    raw = row.get("jcs", row.get("jcs_display", 0.0))
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str) and "/" in raw:
        try:
            num, den = raw.split("/")
            den = float(den)
            return float(num) / den if den > 0 else 0.0
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(raw)
    except (ValueError, TypeError):
        return float(row.get("jcs_display", 0.0))


def map_row(row: dict) -> dict:
    """
    Maps a JSONL audit record to the mutante-semantic document schema.
    Field aliases handle both batch_results.jsonl and demo_data.jsonl layouts.
    """
    jcs_val = _parse_jcs(row)
    final_verdict = row.get("final_verdict", "BLOCKED")

    return {
        "prompt_id":      row.get("prompt_id", ""),
        "mutation":       row.get("mutation_type", row.get("mutation", "unknown")),
        "jcs":            jcs_val,
        "jcs_display":    float(row.get("jcs_display", jcs_val)),
        "final_verdict":  final_verdict,
        "success":        final_verdict == "BYPASSED",
        "indicators":     row.get("indicators", []),
        "layer_matches":  row.get("layer_matches", []),
        "synergy_events": row.get("synergy_events", []),
        "bsv":            row.get("bsv", {}),
        "category":       row.get("category", ""),
        "original_prompt": row.get("original_prompt", ""),
        "mutated_prompt":  row.get("mutated_prompt", ""),
        "timestamp":      row.get("timestamp",
                             datetime.now(timezone.utc).isoformat()),
        # prompt_vector intentionally absent:
        # _render_scatter_plot() activates random-projection fallback when
        # len(vectors) < 2, so the attack_families page degrades gracefully.
    }


def reimport() -> None:
    print(f"Target index : {SEMANTIC_INDEX}")
    print("─" * 50)

    print("→ Ensuring index exists with correct mapping...")
    if not ensure_semantic_index():
        print("✗  Could not create/verify index. Check ELASTIC_CLOUD_ID / ELASTIC_API_KEY.")
        sys.exit(1)
    print("✓  Index ready.\n")

    es = _es()
    sources = [
        os.path.join(ROOT, "batch_results.jsonl"),
        os.path.join(ROOT, "demo_data.jsonl"),
    ]

    seen_ids: set = set()
    ok = err = skipped = 0

    for fpath in sources:
        fname = os.path.basename(fpath)
        if not os.path.exists(fpath):
            print(f"  skip : {fname} not found")
            continue

        with open(fpath, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        print(f"→ Importing {fname}  ({len(lines)} lines)")

        for line in lines:
            try:
                row = json.loads(line)
                pid = row.get("prompt_id", "")

                if pid and pid in seen_ids:
                    skipped += 1
                    continue
                if pid:
                    seen_ids.add(pid)

                doc = map_row(row)
                es.index(index=SEMANTIC_INDEX, document=doc)
                ok += 1

            except Exception as exc:
                err += 1
                print(f"    error: {exc}")

        print(f"  done  ({ok} indexed so far)\n")

    print("─" * 50)
    print(f"✓  Reimport complete")
    print(f"   Indexed  : {ok}")
    print(f"   Skipped  : {skipped}  (duplicates by prompt_id)")
    print(f"   Errors   : {err}")
    print(f"\nNote: no prompt_vector in source data.")
    print("      Attack Families page will show PCA fallback (random projection).")
    print("      Re-run the agent pipeline to regenerate real embeddings.")


if __name__ == "__main__":
    reimport()
