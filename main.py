#!/usr/bin/env python3
# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
main.py — MUTANTE Batch Orchestrator (Legacy, mantenido por compatibilidad).
Para producción usar run_campaign.py.
"""

import os
import sys
import json
import asyncio
import pandas as pd
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent_mutante.engine.mutator import MutationEngine, MUTATIONS_V2
from agent_mutante.engine.mutante_semiotic_evaluator import evaluate_bypass
from agent_mutante.engine.bayesian import ThompsonSamplingOrchestrator
from agent_mutante.engine.quality_gate import BypassQualityGate
from agent_mutante.engine.mutante_client import call_target_async, TARGET_MODEL

# BigQuery sink
try:
    from agent_mutante.engine.bigquery_sink import BigQuerySink
    bq_sink = BigQuerySink()
except Exception as e:
    bq_sink = None
    print(f"[!] BigQuery sink unavailable: {e}", file=sys.stderr)

DATASET_PATH = os.getenv("DATASET_PATH", os.path.join(BASE_DIR, "jailbreaks_dataset_master.csv"))
BATCH_SIZE = int(os.getenv("MUTANTE_BATCH_SIZE", "50"))

mutator = MutationEngine()
gate = BypassQualityGate()
mutations = [
    m.strip() for m in os.getenv("MUTANTE_MUTATIONS", ",".join(MUTATIONS_V2)).split(",")
    if m.strip()
]
bandit = ThompsonSamplingOrchestrator(mutations)

server_params = StdioServerParameters(
    command="python",
    args=[os.path.join(BASE_DIR, "mcp_mutante.py")],
    env={**os.environ},
)


class _BQVerdict:
    def __init__(self, verdict: dict, raw_response: str, model_version: str):
        self.prompt_id = verdict["prompt_id"]
        self.mutation_type = verdict["mutation_type"]
        self.final_verdict = verdict["final_verdict"]
        self.indicators = verdict["indicators"]
        self.timestamp = verdict["timestamp"]
        self.model_version = model_version
        self.raw_response = raw_response[:2000] if raw_response else ""
        self.jcs_breakdown = {
            "bsv": verdict.get("bsv", {}),
            "layer_matches": verdict.get("layer_matches", []),
            "synergy_events": verdict.get("synergy_events", []),
        }
        raw_jcs = verdict.get("jcs_display", verdict.get("jcs", 0))
        try:
            self.jcs = float(raw_jcs)
        except (ValueError, TypeError):
            try:
                num, den = str(raw_jcs).split("/")
                self.jcs = int(num) / int(den)
            except Exception:
                self.jcs = 0.0


async def run_iteration(session: ClientSession, prompt: str, index: int) -> dict:
    mutation = bandit.select_mutation()
    mutated = mutator.apply(prompt, mutation)
    response_text = await call_target_async(mutated)

    verdict = evaluate_bypass(
        prompt_id=f"P-{index:04d}",
        mutation_type=mutation,
        response_text=response_text,
        model_version=TARGET_MODEL,
    )

    is_success = (verdict["final_verdict"] == "BYPASSED")
    bandit.update(mutation, is_success)

    payload = {
        "original_prompt": prompt,
        "mutation": verdict["mutation_type"],
        "mutated_prompt": mutated,
        "response_hash": verdict["raw_response_hash"],
        "success": is_success,
        "jcs": verdict["jcs"],
        "jcs_display": verdict["jcs_display"],
        "indicators": verdict["indicators"],
        "layer_matches": verdict["layer_matches"],
        "synergy_events": verdict["synergy_events"],
        "bsv": verdict["bsv"],
        "probs": bandit.get_probs(),
    }

    try:
        await session.call_tool(
            "indexar_brecha_en_elastic",
            arguments={"breach_data": json.dumps(payload, ensure_ascii=False)},
        )
        print(f"[+] {mutation} | JCS: {verdict['jcs_display']:.2f} | Verdict: {verdict['final_verdict']} | Elastic OK")
        if bq_sink:
            try:
                ok = bq_sink.stream_verdict(_BQVerdict(verdict, response_text, TARGET_MODEL))
                print("    └─ BigQuery OK" if ok else "    └─ BigQuery: insertion errors")
            except Exception as bq_err:
                print(f"    └─ BigQuery error: {bq_err}", file=sys.stderr)
    except Exception as e:
        print(f"[-] MCP Error: {e}", file=sys.stderr)

    return verdict


async def main():
    if not os.path.exists(DATASET_PATH):
        print(f"[-] Dataset not found: {DATASET_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    jailbreaks = (
        df[df["type"] == "jailbreak"]["prompt"].tolist()
        if "type" in df.columns
        else df["prompt"].tolist()
    )
    print(f"[+] Loaded: {len(jailbreaks)} prompts from {DATASET_PATH}")

    batch_verdicts = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for i, prompt in enumerate(jailbreaks[:BATCH_SIZE]):
                print(f"\n[Iteration {i + 1}]")
                verdict = await run_iteration(session, prompt, i + 1)
                batch_verdicts.append(verdict)
                await asyncio.sleep(1)

    passed, gate_report = gate.evaluate_batch_quality(batch_verdicts)
    print("=" * 50)
    print(f"Quality Gate: {'PASSED' if passed else 'FAILED'}")
    print(f"Reason: {gate_report['reason']}")
    print(f"Detail: {gate_report['detail']}")
    print(f"Metrics: {gate_report.get('metrics', {})}")
    print("=" * 50)
    print("[+] Final Bandit Probs:", bandit.get_probs())


if __name__ == "__main__":
    asyncio.run(main())
