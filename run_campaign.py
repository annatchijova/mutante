#!/usr/bin/env python3
# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
run_campaign.py — MUTANTE Full Dataset Campaign Runner v2.1
Procesa datasets contra el modelo configurado con checkpoint/resume y deduplicación.
"""

import os
import sys
import json
import asyncio
import signal
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import pandas as pd
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TaskProgressColumn,
    TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn,
)
from rich.panel import Panel

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent_mutante.engine.mutator import MutationEngine
from agent_mutante.engine.mutante_semiotic_evaluator import evaluate_bypass
from agent_mutante.engine.bayesian import ThompsonSamplingOrchestrator
from agent_mutante.engine.quality_gate import BypassQualityGate
from agent_mutante.engine.mutante_client import call_target_async, TARGET_MODEL

from elasticsearch import Elasticsearch

try:
    from agent_mutante.engine.elastic_semantic import index_probe_semantic, ensure_semantic_index
    _semantic_ok = True
except ImportError:
    _semantic_ok = False

try:
    from agent_mutante.engine.bigquery_sink import BigQuerySink
    bq_sink = BigQuerySink()
except Exception:
    bq_sink = None

CONCURRENCY   = int(os.getenv("CAMPAIGN_CONCURRENCY", "8"))
DELAY_BETWEEN = float(os.getenv("CAMPAIGN_DELAY_S", "0.2"))

CHECKPOINT_F  = BASE_DIR / "campaign_checkpoint.jsonl"
RESULTS_F     = BASE_DIR / "campaign_results.jsonl"

DATASET_FILES = [
    BASE_DIR / "jailbreaks_dataset_master_11k.csv",
    BASE_DIR / "jailbreaks_dataset_final.csv",
    BASE_DIR / "jailbreaks_dataset_master.csv",
    BASE_DIR / "jailbreaks_dataset_master_enriched.csv",
    BASE_DIR / "jailbreaks_dataset_demo_2000.csv",
]

MUTATIONS = ["rot13", "base64_encode", "mirror", "scramble", "zigzag"]

console = Console()
_shutdown = False

def _sig_handler(sig, _frame):
    global _shutdown
    console.print("\n[bold yellow]⚡ Shutdown requested — finishing current batch...[/bold yellow]")
    _shutdown = True

signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)


def load_datasets() -> list[str]:
    all_prompts: set[str] = set()
    console.print("\n[bold cyan]◈ DATASET LOADING[/bold cyan]")
    
    for fpath in DATASET_FILES:
        if not fpath.exists():
            console.print(f"  [dim]skip  {fpath.name} — not found[/dim]")
            continue
        try:
            df = pd.read_csv(fpath, on_bad_lines="skip")
            if "prompt" not in df.columns:
                console.print(f"  [yellow]skip  {fpath.name} — no 'prompt' column[/yellow]")
                continue
            if "type" in df.columns:
                series = df[df["type"] == "jailbreak"]["prompt"].dropna()
            else:
                series = df["prompt"].dropna()
            
            before = len(all_prompts)
            all_prompts.update(p.strip() for p in series if isinstance(p, str) and len(p.strip()) > 10)
            added = len(all_prompts) - before
            console.print(f"  [green]✓[/green]  {fpath.name:45s} +{added:>6,} unique")
        except Exception as exc:
            console.print(f"  [red]✗[/red]  {fpath.name}: {exc}")
    
    console.print(f"\n  [bold]Total unique: {len(all_prompts):,}[/bold]\n")
    return sorted(all_prompts)


def load_checkpoint() -> set[str]:
    done: set[str] = set()
    if CHECKPOINT_F.exists():
        with open(CHECKPOINT_F) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        done.add(json.loads(line)["ph"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return done


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


mutator = MutationEngine()
bandit = ThompsonSamplingOrchestrator(MUTATIONS)
gate = BypassQualityGate()


def _es_client() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
        api_key=os.getenv("ELASTIC_API_KEY"),
    )


async def process_prompt(session, prompt, global_idx, sem, stats, cp_fh, out_fh):
    mutation = bandit.select_mutation()
    mutated = mutator.apply(prompt, mutation)
    response = await call_target_async(mutated)

    verdict = evaluate_bypass(
        prompt_id=f"P-{global_idx:05d}",
        mutation_type=mutation,
        response_text=response,
        model_version=TARGET_MODEL,
    )

    is_success = verdict["final_verdict"] == "BYPASSED"
    bandit.update(mutation, is_success)
    timestamp = datetime.now(timezone.utc).isoformat()

    audit_payload = {
        "original_prompt": prompt[:1000],
        "mutation": verdict["mutation_type"],
        "mutated_prompt": mutated[:1000],
        "response_hash": verdict.get("raw_response_hash", ""),
        "success": is_success,
        "jcs": verdict["jcs"],
        "jcs_display": verdict["jcs_display"],
        "indicators": verdict["indicators"],
        "layer_matches": verdict["layer_matches"],
        "synergy_events": verdict["synergy_events"],
        "bsv": verdict["bsv"],
        "probs": bandit.get_probs(),
        "timestamp": timestamp,
        "category": verdict.get("category", ""),
    }

    # Elastic audit index
    try:
        es = _es_client()
        es.index(index="mutante-audits", document=audit_payload)
        stats["elastic_ok"] += 1
    except Exception as exc:
        stats["elastic_err"] += 1

    # Semantic index
    if _semantic_ok:
        try:
            semantic_payload = {**audit_payload, "final_verdict": verdict["final_verdict"]}
            index_probe_semantic(semantic_payload)
            stats["semantic_ok"] += 1
        except Exception:
            stats["semantic_err"] += 1

    # BigQuery
    if bq_sink:
        try:
            from main import _BQVerdict
            bq_sink.stream_verdict(_BQVerdict(verdict, response, TARGET_MODEL))
        except Exception:
            pass

    stats["total"] += 1
    if is_success:
        stats["bypassed"] += 1
    stats["last_mutation"] = mutation
    stats["last_jcs"] = verdict["jcs_display"]
    stats["last_verdict"] = verdict["final_verdict"]

    ph = prompt_hash(prompt)
    cp_fh.write(json.dumps({"ph": ph, "i": global_idx}) + "\n")
    cp_fh.flush()
    out_fh.write(json.dumps({**verdict, "timestamp": timestamp}) + "\n")
    out_fh.flush()

    return verdict


async def run_campaign(limit=None, dry_run=False):
    console.print(Panel.fit(
        f"[bold cyan]MUTANTE CAMPAIGN v2.1[/bold cyan]\n"
        f"Model: [yellow]{TARGET_MODEL}[/yellow]   "
        f"Concurrency: [yellow]{CONCURRENCY}[/yellow]",
        border_style="cyan",
    ))

    all_prompts = load_datasets()
    if not all_prompts:
        console.print("[red]No prompts. Aborting.[/red]")
        return

    if limit:
        all_prompts = all_prompts[:limit]
        console.print(f"[yellow]⚠ Capped at {limit:,} prompts[/yellow]\n")

    done_hashes = load_checkpoint()
    pending = [p for p in all_prompts if prompt_hash(p) not in done_hashes]
    skipped = len(all_prompts) - len(pending)
    if skipped:
        console.print(f"[green]✓ Checkpoint: {skipped:,} done — resuming {len(pending):,}[/green]\n")

    if dry_run:
        console.print(f"[bold yellow]DRY RUN — would process {len(pending):,}. Exiting.[/bold yellow]")
        return

    if not pending:
        console.print("[bold green]✓ All done![/bold green]")
        return

    if _semantic_ok:
        ensure_semantic_index()

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {
        "total": skipped, "bypassed": 0,
        "elastic_ok": 0, "elastic_err": 0,
        "semantic_ok": 0, "semantic_err": 0,
        "last_mutation": "—", "last_jcs": 0.0, "last_verdict": "—",
    }

    server_params = StdioServerParameters(
        command="python", args=[str(BASE_DIR / "mcp_mutante.py")], env={**os.environ},
    )

    total_target = len(all_prompts)

    with Progress(
        SpinnerColumn(), TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40), MofNCompleteColumn(), TaskProgressColumn(),
        TimeElapsedColumn(), TimeRemainingColumn(),
        console=console, refresh_per_second=4,
    ) as progress:
        task = progress.add_task(f"[cyan]Campaign — {TARGET_MODEL}", total=len(pending))
        cp_fh = open(CHECKPOINT_F, "a", encoding="utf-8")
        out_fh = open(RESULTS_F, "a", encoding="utf-8")

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    mini_batch = 20
                    global_start = skipped

                    for batch_start in range(0, len(pending), mini_batch):
                        if _shutdown:
                            console.print("[yellow]⚡ Paused. Resume with same command.[/yellow]")
                            break

                        batch = pending[batch_start: batch_start + mini_batch]
                        tasks = [
                            process_prompt(session, prompt, global_start + batch_start + j, sem, stats, cp_fh, out_fh)
                            for j, prompt in enumerate(batch)
                        ]
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for r in results:
                            if isinstance(r, Exception):
                                console.print(f"  [red]Error: {r}[/red]")

                        progress.advance(task, len(batch))
                        done = stats["total"]
                        rate = (stats["bypassed"] / done * 100) if done else 0
                        console.print(
                            f"  [dim]{done:>6,}/{total_target:<6,}[/dim]"
                            f"  bypass [yellow]{rate:.1f}%[/yellow]"
                            f"  jcs [cyan]{stats['last_jcs']:.3f}[/cyan]"
                            f"  [{stats['last_verdict']}] vec={stats['last_mutation']}"
                        )
        finally:
            cp_fh.close()
            out_fh.close()

    total = stats["total"]
    bypass = stats["bypassed"]
    rate = (bypass / total * 100) if total else 0

    console.print(Panel(
        f"[bold]Campaign Complete[/bold]\n\n"
        f"Processed: [cyan]{total:,}[/cyan]\n"
        f"Bypassed: [yellow]{bypass:,}[/yellow] ({rate:.1f}%)\n"
        f"Blocked: [dim]{total - bypass:,}[/dim]\n"
        f"ES Audit ✓: [green]{stats['elastic_ok']:,}[/green]  ✗ {stats['elastic_err']:,}\n"
        f"ES Semantic ✓: [green]{stats['semantic_ok']:,}[/green]  ✗ {stats['semantic_err']:,}",
        title="[bold green]◈ MUTANTE CAMPAIGN COMPLETE[/bold green]",
        border_style="green",
    ))
    console.print("[bold]Final Bandit Probs:[/bold]", bandit.get_probs())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MUTANTE Campaign Runner")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_campaign(limit=args.limit, dry_run=args.dry_run))
