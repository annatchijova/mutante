#!/usr/bin/env python3
# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
run_campaign.py — MUTANTE Campaign Runner v3.0
Uses ProbeSourceRegistry + MutationSourceRegistry for pluggable corpora and mutations.
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
from typing import List, Optional

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TaskProgressColumn,
    TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn,
)
from rich.panel import Panel
from rich.table import Table

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# New registry-based imports
from agent_mutante.probe_sources import (
    ProbeSourceRegistry,
    NormalizedProbe,
)
from agent_mutante.probe_sources.mutation_source import MutationSourceRegistry
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

console = Console()
_shutdown = False


def _sig_handler(sig, _frame):
    global _shutdown
    console.print("\n[bold yellow]⚡ Shutdown requested — finishing current batch...[/bold yellow]")
    _shutdown = True

signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)


def load_all_probes(
    categories: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[NormalizedProbe]:
    """Load probes from all enabled sources, optionally filtered."""
    all_probes: List[NormalizedProbe] = []
    seen_hashes = set()

    # Auto-register probe sources by importing them
    _register_probe_sources()

    probe_sources = ProbeSourceRegistry.get_all(enabled_only=True)
    
    for source in probe_sources:
        # Filter by category/source if specified
        if categories and source.category not in categories:
            continue
        if sources and source.name not in sources:
            continue
        
        console.print(f"[cyan]Loading probes from {source.category}:{source.name}...[/cyan]")
        try:
            probes = source.load()
            if not probes:
                err = getattr(source, "last_sync_error", None)
                suffix = f" — {err}" if err else ""
                console.print(f"  [dim]No probes loaded{suffix}[/dim]")
                continue
            
            # Deduplicate by prompt hash
            unique_probes = []
            for probe in probes:
                ph = hashlib.sha256(probe.prompt.encode()).hexdigest()[:16]
                if ph not in seen_hashes:
                    seen_hashes.add(ph)
                    unique_probes.append(probe)
            
            if limit and len(all_probes) + len(unique_probes) > limit:
                unique_probes = unique_probes[:limit - len(all_probes)]
            
            all_probes.extend(unique_probes)
            console.print(f"  [green]✓[/green]  +{len(unique_probes)} unique (total: {len(all_probes)})")
            
            if limit and len(all_probes) >= limit:
                break
                
        except Exception as exc:
            console.print(f"  [red]✗[/red]  {source.category}:{source.name}: {exc}")
    
    console.print(f"\n  [bold]Total unique probes: {len(all_probes):,}[/bold]\n")
    return all_probes


def _register_probe_sources():
    """Import probe source modules to trigger @register_source decorators."""
    try:
        from agent_mutante.probe_sources import garak_probe_source, odin_probe_source, generic_probe_source
    except ImportError:
        pass  # Sources already registered or not available


def get_mutation_names(enabled_only: bool = True) -> List[str]:
    """Get available mutation family names from registry."""
    _register_mutation_sources()
    return MutationSourceRegistry.get_names(enabled_only=enabled_only)


def _register_mutation_sources():
    """Import mutation source modules to trigger @register_mutation decorators."""
    try:
        from agent_mutante.probe_sources import mutation_source
    except ImportError:
        pass


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


def _es_client() -> Elasticsearch:
    return Elasticsearch(
        cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
        api_key=os.getenv("ELASTIC_API_KEY"),
    )


async def process_prompt(
    session,
    probe: NormalizedProbe,
    global_idx: int,
    sem: asyncio.Semaphore,
    stats: dict,
    cp_fh,
    out_fh,
    bandit: ThompsonSamplingOrchestrator,
):
    async with sem:
        return await _process_prompt_inner(
            session, probe, global_idx, stats, cp_fh, out_fh, bandit
        )


async def _process_prompt_inner(
    session,
    probe: NormalizedProbe,
    global_idx: int,
    stats: dict,
    cp_fh,
    out_fh,
    bandit: ThompsonSamplingOrchestrator,
):
    # Select mutation from bandit (uses enabled mutation families)
    mutation = bandit.select_mutation()
    
    # Get mutation engine and apply
    mutation_engine = MutationSourceRegistry.get(mutation)
    if mutation_engine:
        mutated = mutation_engine.apply(probe.prompt)
    else:
        # Fallback to built-in
        from agent_mutante.engine.mutator import MutationEngine as BuiltinMutator
        mutated = BuiltinMutator().apply(probe.prompt, mutation)
    
    response = await call_target_async(mutated)

    verdict = evaluate_bypass(
        prompt_id=f"P-{global_idx:05d}",
        mutation_type=mutation,
        response_text=response,
        model_version=TARGET_MODEL,
        category=probe.category,
    )

    is_success = verdict["final_verdict"] == "BYPASSED"
    bandit.update(mutation, is_success)
    timestamp = datetime.now(timezone.utc).isoformat()

    audit_payload = {
        "original_prompt": probe.prompt[:1000],
        "probe_id": probe.probe_id,
        "probe_category": probe.category,
        "probe_source": probe.source,
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
        "category": probe.category,
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

    ph = prompt_hash(probe.prompt)
    cp_fh.write(json.dumps({"ph": ph, "i": global_idx, "probe_id": probe.probe_id}) + "\n")
    cp_fh.flush()
    out_fh.write(json.dumps({**verdict, "timestamp": timestamp, "probe_id": probe.probe_id}) + "\n")
    out_fh.flush()

    return verdict


async def run_campaign(
    limit: Optional[int] = None,
    dry_run: bool = False,
    categories: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    mutation_families: Optional[List[str]] = None,
):
    # Load probes from registry
    all_probes = load_all_probes(categories=categories, sources=sources, limit=limit)
    if not all_probes:
        console.print("[red]No probes loaded. Aborting.[/red]")
        return

    # Get available mutations
    available_mutations = get_mutation_names()
    if mutation_families:
        available_mutations = [m for m in available_mutations if m in mutation_families]
        if not available_mutations:
            console.print(f"[red]No valid mutation families from: {mutation_families}[/red]")
            return

    console.print(f"[cyan]Available mutations: {', '.join(available_mutations)}[/cyan]")

    # Initialize bandit with available mutations
    bandit = ThompsonSamplingOrchestrator(available_mutations)
    gate = BypassQualityGate()

    done_hashes = load_checkpoint()
    pending = [p for p in all_probes if prompt_hash(p.prompt) not in done_hashes]
    skipped = len(all_probes) - len(pending)
    if skipped:
        console.print(f"[green]✓ Checkpoint: {skipped:,} done — resuming {len(pending):,}[/green]\n")

    if dry_run:
        console.print(f"[bold yellow]DRY RUN — would process {len(pending):,}. Exiting.[/bold yellow]")
        # Show probe breakdown
        table = Table(title="Probe Breakdown")
        table.add_column("Category")
        table.add_column("Source")
        table.add_column("Count", justify="right")
        from collections import Counter
        cat_counts = Counter((p.category, p.source) for p in pending)
        for (cat, src), count in cat_counts.most_common():
            table.add_row(cat, src, str(count))
        console.print(table)
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

    total_target = len(all_probes)

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
                            process_prompt(
                                session, prompt, global_start + batch_start + j, sem, stats, cp_fh, out_fh, bandit
                            )
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

    # Final bandit probs table
    probs_table = Table(title="Final Bandit Probabilities")
    probs_table.add_column("Mutation")
    probs_table.add_column("P(bypass)", justify="right")
    for mut, prob in sorted(bandit.get_probs().items(), key=lambda x: -x[1]):
        probs_table.add_row(mut, f"{prob:.3f}")
    console.print(probs_table)

    # Quality gate on final batch
    if total > 0:
        # Load recent verdicts for quality gate
        recent_verdicts = []
        if RESULTS_F.exists():
            with open(RESULTS_F) as f:
                for line in f:
                    try:
                        recent_verdicts.append(json.loads(line))
                    except Exception:
                        pass
        if recent_verdicts:
            passed, report = gate.evaluate_batch_quality(recent_verdicts[-100:])  # last 100
            console.print(f"\n[bold]Quality Gate (last 100):[/bold] {'✓ PASSED' if passed else '✗ FAILED'} — {report['reason']}")


def main():
    parser = argparse.ArgumentParser(description="MUTANTE Campaign Runner v3.0")
    parser.add_argument("--limit", type=int, default=None, help="Max probes to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--category", action="append", help="Filter by probe category (e.g. garak, odin, harmbench)")
    parser.add_argument("--source", action="append", help="Filter by probe source name")
    parser.add_argument("--mutations", action="append", help="Restrict to specific mutation families")
    parser.add_argument("--list-sources", action="store_true", help="List registered probe sources and exit")
    parser.add_argument("--list-mutations", action="store_true", help="List registered mutation families and exit")
    args = parser.parse_args()

    _register_probe_sources()
    _register_mutation_sources()

    if args.list_sources:
        sources = ProbeSourceRegistry.list_registered()
        table = Table(title="Registered Probe Sources")
        table.add_column("Category")
        table.add_column("Name")
        table.add_column("Enabled")
        for s in sources:
            table.add_row(s["category"], s["name"], "✓" if s["enabled"] else "✗")
        console.print(table)
        return

    if args.list_mutations:
        enabled = {m["name"]: m["enabled"] for m in MutationSourceRegistry.list_registered()}
        table = Table(title="Registered Mutation Families")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Enabled")
        for m in MutationSourceRegistry.get_all(enabled_only=False):
            table.add_row(m.name, m.description, "✓" if enabled[m.name] else "✗")
        console.print(table)
        return

    asyncio.run(run_campaign(
        limit=args.limit,
        dry_run=args.dry_run,
        categories=args.category,
        sources=args.source,
        mutation_families=args.mutations,
    ))


if __name__ == "__main__":
    main()
