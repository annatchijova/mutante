# Security Audit — MUTANTE probe_sources refactor (uncommitted work)

## Red Team Round 1

**Date:** 2026-10-05  **Method:** Abductive Engineering (A–D–I) + Red-Team Auditing
**Scope:** `agent_mutante/probe_sources/` (new package) and `run_campaign.py` v3.0 registry refactor.
Out of scope: `mutante_semiotic_evaluator`, `bayesian` orchestrator internals, dashboard, MCP server.
**Base:** `main` @ `ea86564` (uncommitted working-tree changes)  **Reproducible evidence:** commands inline below.

## Threat model

- Attacker CAN: control the contents of corpus files (CSV/JSON/JSONL datasets pulled from third parties) and the output of external tools the sources shell out to (e.g. a compromised `garak` install or poisoned `--list_probes` output).
- Attacker CANNOT: modify repository code, inject config at runtime (sources are configured in code at registration time), or access the operator's shell.

## Epistemic legend

CODE FACT · PLAUSIBLE HYPOTHESIS · CONFIRMED BY INDUCTION · FALSIFIED

## Executive summary

| ID | Severity | Level | Module | Finding |
|----|----------|-------|--------|---------|
| RT-1 | Medium | CONFIRMED BY INDUCTION (fix verified) | `garak_probe_source.py` | `python -c` string interpolation of `probe_name` → code injection if garak output is hostile |
| RT-2 | Medium | CONFIRMED BY INDUCTION | `generic_probe_source.py` | `prompt_column`/`id_column` config was dead — HarmBench source yielded 0 of 400 real behaviors |
| RT-3 | Medium | CONFIRMED BY INDUCTION | `generic_probe_source.py` | `csv.field_size_limit` default (128 KiB) crashes on legacy jailbreak CSVs with large fields |
| RT-4 | Medium | CONFIRMED BY INDUCTION | `run_campaign.py` | Legacy jailbreak corpora (~16k prompts) silently dropped by refactor — dry run loaded 0 probes total |
| RT-5 | Low | CONFIRMED BY INDUCTION | `mutation_source.py` | `unicode_tags`/`homoglyph` mutations non-deterministic (unseeded `random`) — mutated attack not reproducible |
| RT-6 | Low | CONFIRMED BY INDUCTION | `mutation_source.py` | `CompositeMutation` self-reference in `sequence` config → unbounded recursion |
| RT-7 | Low | CODE FACT | `__init__.py` | `_auto_import_submodules()` invoked mid-file where `NormalizedProbe` is undefined — registration only worked via the second call |
| RT-8 | Low | CODE FACT | `__init__.py`, sources | `synced_at` never written by generic/odin sources → `needs_sync` always true (cache defeated); sync errors swallowed silently by `load()` |
| RT-9 | Low | CODE FACT | `garak_probe_source.py` | Hardcoded `python` binary — fails on systems with only `python3` |

## Findings

### RT-1 — Command injection via `probe_name` in `python -c` (FIXED)
**Severity:** Medium  **Level:** CONFIRMED BY INDUCTION (mechanism confirmed by code shape; fix verified by execution)  **Bucket:** vulnerability

- **Surprise:** `subprocess.run(["python", "-c", f"...garak.probes.get('{probe_name}')..."])` interpolates `probe_name` — taken verbatim from `garak --list_probes` stdout — into evaluated code.
- **Causal chain:** hostile garak output line → `'` + payload inside `-c` string → arbitrary code execution under the campaign's interpreter.
- **Threat-model precondition:** attacker controls `garak --list_probes` output (compromised dependency or manipulated environment).
- **Fix:** `probe_name` now passed as `sys.argv[1]` to a constant `-c` script; never evaluated. All `python` invocations switched to `sys.executable` (also fixes RT-9).
- **Induction:** ran the new argv form with payload `x');import os;os.system('touch /tmp/PWNED');('` → argv arrives literally, no `/tmp/PWNED` created.

### RT-2 — Dead config columns broke HarmBench (FIXED)
**Severity:** Medium  **Level:** CONFIRMED BY INDUCTION  **Bucket:** defect (correctness)

- `GenericProbeSource.sync()` passed raw dicts to `normalize_probes`, which only reads `prompt`/`text`/`content`/`id` keys; the `prompt_column`/`id_column` config was never consulted. Additionally `HarmBenchProbeSource` shipped defaults matching a different schema (`prompt`, `type=="jailbreak"`) than the repo's actual `harmbench_behaviors.csv` (`Behavior`, `BehaviorID`, no `type` column) — every row filtered out.
- **Induction:** `run_campaign.py --dry-run` before fix → harmbench `+0` (sync_version `count: 0`); after remap + schema fix → `+393`.
- **Fix:** `sync()` now remaps configured columns to canonical keys before normalization; HarmBench defaults corrected to the real schema.

### RT-3 — `csv` field limit crash on legacy corpora (FIXED)
**Severity:** Medium  **Level:** CONFIRMED BY INDUCTION  **Bucket:** defect

- `csv.DictReader` default field limit (131072) is exceeded by prompts in the legacy jailbreak CSVs — the previous pandas loader tolerated this via `on_bad_lines="skip"`; the new loader crashed inside `sync()` and returned 0 with only an error dict.
- **Induction:** `csv.Error: field larger than field limit (131072)` reproduced on `jailbreaks_dataset_master_11k.csv`; resolved by `csv.field_size_limit(1 GiB)`.

### RT-4 — Silent corpus regression (FIXED)
**Severity:** Medium  **Level:** CONFIRMED BY INDUCTION  **Bucket:** defect (behavioral regression)

- The refactor removed `DATASET_FILES` without registering any source for the existing jailbreak CSVs; combined with RT-2, the campaign loaded **0 probes**.
- **Fix:** four `jailbreaks:` sources registered via `_legacy_jailbreak_source` factory (master_11k, final, master, enriched).
- **Induction:** dry run before → `Total unique probes: 0`; after → `7,497` (global dedup across sources).
- **Intentional divergence (documented):** `master_11k` loads unfiltered — its labels are `successful_jailbreak`/`unsuccessful_jailbreak` (both attack prompts); the old `type == "jailbreak"` filter had silently contributed 0 rows from this file.

### RT-5 — Non-deterministic mutations (FIXED)
**Severity:** Low  **Level:** CONFIRMED BY INDUCTION  **Bucket:** invariant (determinism)

- `unicode_tags` and `homoglyph` used unseeded `random.random()`: identical input produced different mutated attacks per run — an evaluation pipeline whose attack string cannot be reproduced. `scramble` already seeded per word (`Random(word)`).
- **Fix:** `rng = random.Random(text)` per `apply`, matching the existing convention.
- **Induction:** `homoglyph.apply('Hello World abc')` → `'Hеlӏo World аbc'` identical across two fresh processes.

### RT-6 — CompositeMutation self-recursion (FIXED)
**Severity:** Low  **Level:** CONFIRMED BY INDUCTION  **Bucket:** defect

- A `sequence` config containing `"composite"` recursed without bound. Guard added: a composite skips its own name.
- **Induction:** `configure({'sequence': ['composite','rot13']}).apply('abc')` → `'nop'`, no RecursionError.

### RT-7 — Fragile double auto-import (FIXED)
**Severity:** Low  **Level:** CODE FACT  **Bucket:** defect (latent)

- `_auto_import_submodules()` ran at mid-file (line ~148) where `NormalizedProbe` (line ~191) did not yet exist; all probe-source modules failed import silently (`except ImportError: pass`) and only registered on the second call at EOF. First invocation removed.

### RT-8 — Sync bookkeeping and silent degradation (FIXED)
**Severity:** Low  **Level:** CODE FACT  **Bucket:** defect / honest-degradation

- `write_sync_version` call sites in generic/odin never wrote `synced_at`, so `needs_sync` compared file mtime against `0` → always true → re-sync every load (correct results, cache defeated). Fixed centrally: `write_sync_version` now stamps `synced_at = time.time()` via `setdefault`.
- `load()` discarded `sync()`'s error dict — a broken source printed the same "No probes loaded" as a legitimately empty one (this masked RT-2 for an unknown period). Fixed: sources record `last_sync_error`; `run_campaign` prints it (`No probes loaded — Probe file not found: …`).

### RT-9 — Hardcoded `python` interpreter (FIXED)
**Severity:** Low  **Level:** CODE FACT  **Bucket:** defect (portability)

- `garak` source shelled to `python`, absent on systems shipping only `python3` → source always empty there. Now `sys.executable`.

## Discarded (non-exploitable) vectors

| Vector | Result | Why it failed |
|--------|--------|---------------|
| Prompt-hash (SHA-256[:16]) collision across corpus | FALSIFIED | 64-bit space over ~10k prompts; collision probability negligible |
| Checkpoint format break on refactor | FALSIFIED | `load_checkpoint` reads only `ph`, still written; resume is backward compatible |
| Malformed JSONL/JSON rows crashing a campaign | FALSIFIED | `sync()` wraps all parsing; errors degrade to `success: False` + `last_sync_error` |
| Registry duplicate-key DoS | FALSIFIED as vuln | `register` raises ValueError, but registration is code-time, not attacker-reachable — hygiene at most |
| Bandit update lost in refactor | FALSIFIED | `bandit.update(mutation, is_success)` present at `run_campaign.py:230` |

## Recommendations (out of scope — record only)

- `GenericProbeSource` row count is unbounded for JSON/JSONL paths (CSV applies `_limit` early); cap raw loads or stream.
- `odin` variant expansion is multiplicative (`variants × substances`) with no ceiling.
- `_load_json` ignores `_limit` before normalization.
- `session` parameter in `process_prompt`/`_process_prompt_inner` is accepted but unused — pre-existing.
- `enable`/`disable`/`configure` registry APIs exist but nothing exercises them; untested paths.

---

## Red Team Round 2 — Variant analysis

**Method:** each Round-1 bug was abstracted to an invariant (`sink + precondition + violated invariant`) and hunted across sibling implementations and adjacent layers (`beyond-the-sink`). Scope expanded to `mutante_client.py`, `mcp_mutante.py`, `elastic_semantic.py`, `sandbox.py`, `mutante_hybrid_evaluator.py`.

| ID | Severity | Level | Module | Finding |
|----|----------|-------|--------|---------|
| RT-10 | Medium | CONFIRMED BY INDUCTION | `mutante_client.py` + `run_campaign.py` | Infra failures (`BLOCKED_OR_ERROR: HTTP 503`, client not initialized) were evaluated as model responses → verdict BLOCKED → `bandit.update(mutation, False)` trains the Thompson sampler on outage noise AND the checkpoint marks the probe done, so a transient error permanently consumes it |
| RT-11 | Low | CODE FACT | `elastic_semantic.py` | `final_verdict` collapses to `hybrid_verdict` when present — downstream consumers cannot distinguish deterministic from LLM-influenced verdicts (provenance lost at the index boundary) |
| RT-12 | Low | CONFIRMED BY INDUCTION | `mcp_mutante.py` | Sibling mutation implementation diverged: `mirror` did whole-string reversal vs the engine's per-word; `base64`/`espejo` aliases vs registry names; unknown mutation silently returned the prompt **unmutated**; dataset loaded unfiltered (514 benign rows served as attacks) |
| RT-13 | Low | CODE FACT | `run_campaign.py` vs `sandbox.py` | `sandboxed_mcp_spawn` (rlimits + env scrubbing) exists but nothing calls it — campaign spawns MCP via `StdioServerParameters(command="python", env={**os.environ})`: hardcoded `python` (RT-9 variant — crashes where only `python3` exists) and full env passthrough with no sandbox |
| RT-14 | Medium | CODE FACT | `mutante_hybrid_evaluator.py` | Architectural invariant deviation vs CLAUDE.md §5.1: `evaluate_bypass_hybrid` adds an LLM-judged `llm_boost` (×2.5 weight) to the deterministic JCS — the LLM can push a deterministic sub-threshold score over `HYBRID_BYPASS_THRESHOLD` and flip the verdict. Mitigants: separate `hybrid_verdict` field, `evaluator: "hybrid"` tag. **Not fixed** — flagged for maintainer decision (design intent vs. stated invariant) |
| RT-15 | Low | CONFIRMED BY INDUCTION | `probe_sources` `load()` | Latent bug surfaced by the RT-8 fix: version file said "synced" but probes were never persisted — a fresh process with warm sync-version files loaded 0. File-based sources now re-sync whenever the in-memory cache is empty |

### RT-10 — causal chain and verification
```
call_target_async raises / client None
    → returns "BLOCKED_OR_ERROR: <e>" as if it were model text
    → evaluate_bypass → BLOCKED, jcs 0/1   [induction: evaluated twice, 0/1 both]
    → bandit.update(mutation, False)      [outage trains "this mutation fails"]
    → cp_fh.write({ph})                   [probe marked done — never retried on resume]
```
**Fix:** `mutante_client` emits distinct `INFRA_ERROR:` for infra paths (`extract_text`'s `BLOCKED_OR_ERROR` stays for genuine model-side safety blocks). `_process_prompt_inner` detects it: writes a flagged `{infra_error: true}` record to results, skips `bandit.update`, skips the checkpoint write, counts `stats["infra_err"]`; the end-of-campaign quality gate filters flagged rows.
**Induction:** `_process_prompt_inner` with stubbed `INFRA_ERROR` response → flagged record written, checkpoint empty, `bandit.get_probs()` unchanged.

### RT-13 — verification
`grep sandboxed_mcp_spawn` → only its own definition. `command="python"` → `sys.executable`. The rlimit/env-scrub sandbox remains unwired (`StdioServerParameters` has no `preexec_fn` channel) — recorded as a gap, not silently wired.

### Round-2 discarded vectors

| Vector | Result | Why |
|--------|--------|-----|
| Floats in `bsv`/layer scores corrupting canonical verdict | FALSIFIED | canonical `jcs` is stored as `"num/den"` Fraction string; floats are display/telemetry only, derived deterministically from Fractions |
| `evaluate_bypass` category kwarg mismatch | FALSIFIED | signature accepts `category`; verdict returns it; audit_payload consistent |
| MCP `indexar_brecha_en_elastic` arbitrary JSON index | Hygiene | stdio-local tool, caller-trusted boundary; no auth model promised |
| `python` literal elsewhere | one hit fixed | `StdioServerParameters(command="python")` → `sys.executable`; no other literal found |

### Round-2 recommendations (recorded, not acted on)

- Decide the fate of the hybrid evaluator (RT-14): either document the deliberate §5.1 exception in the module + downstream schema, or gate `hybrid_verdict` behind an explicit opt-in so it can never masquerade as a deterministic verdict.
- Wire `sandboxed_mcp_spawn`'s env scrubbing into the campaign spawn path (needs an MCP-transport-compatible way to pass `preexec_fn`, or scrub `env` inline).
- `quality_gate` reads all of `campaign_results.jsonl` to take the last 100 — O(file) tail; fine at current scale.
- `from main import _BQVerdict` inside the per-prompt loop couples campaign code to the Streamlit app module; works via import caching, but fragile.

---

## Red Team Round 3 — Emergent / architectural

**Method:** composition breaks, trust-boundary gaps, authority/provenance loss across the write path (checkpoint → results → Elastic → BigQuery), the ADK agent sibling (`agent.py`), seed tooling (`reseed_elastic.py`), and both dashboard trees (`pages/`, `dashboard/pages/` — verified identical).

| ID | Severity | Level | Module | Finding |
|----|----------|-------|--------|---------|
| RT-16 | Low | CODE FACT | `run_campaign.py` | Write-order hazard: checkpoint flushed **before** the result row — a crash in between loses the verdict AND burns the probe (marked done). Swapped: result first, checkpoint second — a crash now leaves a retryable probe |
| RT-17 | Medium | CONFIRMED BY INDUCTION | `agent.py` | RT-10 sibling: `analyze_prompt` evaluated `INFRA_ERROR`/`BLOCKED_OR_ERROR` strings as responses and trained `_bandit` on them. Fixed symmetrically; induction: stubbed INFRA_ERROR → flagged dict, bandit stays at prior 0.5, `_session_verdicts` empty |
| RT-18 | Low | CODE FACT | dashboards + `elastic_semantic.py` | `sample: true` was written by `reseed_elastic` but never surfaced at read time — synthetic demo docs and real campaign verdicts were indistinguishable in `mutante-audits`/`mutante-semantic` consumers. Fixed: `sample` now propagates through `index_probe_semantic`, `fetch_probes`, `find_similar_attacks`, `discover_attack_families`, and the audit-index row builders (`forensic_feed`, `command_center`, both trees) |
| RT-19 | Info | CODE FACT | `reseed_elastic.py` | Verified honest-degradation done right: `sample:true` on both docs, redacted prompts, `--wipe` explicit, `--dry-run` mirror. Hypothesis "demo data contaminates forensic index silently" — FALSIFIED at write side; gap was read-side only (RT-18) |
| RT-20 | Info | CODE FACT | `semiotic_llm_judge.py` | Judge degrades honestly: any failure sets `error` → `degradation_vector_to_jcs_boost` returns 0.0 → hybrid converges to deterministic score. No silent partial contribution |

### Round-3 verification

- `python3 test_demo_pipeline.py`: **16/16 offline tests pass**; `test_bayesian.py`: **6/6 pass**. The one manual-runner failure (`test_integration_demo_set_runs`) is a pre-existing live-integration smoke test requiring `agent_mutante/engine` on sys.path and a live target — not a regression.
- `run_campaign.py --dry-run` (fresh process, warm sync-versions): 7,497 probes — cold-cache path holds.
- `agent.analyze_prompt` with stubbed `INFRA_ERROR` → `{infra_error: true}`, bandit posterior untouched.

### Round-3 discarded vectors

| Vector | Result | Why |
|--------|--------|-----|
| Synthetic docs contaminating forensic indices | FALSIFIED at write side | `reseed_elastic` marks `sample:true` on both docs; gap was consumer-side only (RT-18) |
| LLM judge partial output on failure | FALSIFIED | `error` key → boost 0.0; no partial contribution path |
| Dashboard divergence (`pages/` vs `dashboard/pages/`) | FALSIFIED as a drift bug | trees are identical copies (diff: only `__init__.py`/`__pycache__`); duplication is a maintenance smell, not a correctness bug — recorded below |

### Round-3 recommendations (recorded, not acted on)

- `pages/` and `dashboard/pages/` are a byte-identical copy — pick one or generate one from the other; every future dashboard fix otherwise lands twice.
- ES|QL analytics queries (`ESQL_*`) do not exclude `sample:true` docs — aggregate stats mix synthetic and real telemetry. Decide per-page whether the view is demo or forensic and filter explicitly.
- Two concurrent campaign processes share `campaign_results.jsonl`/`campaign_checkpoint.jsonl` with no lock; large audit rows can interleave mid-line. A lockfile or per-run file naming would close it.
- `attack_family_report` averages `jcs` mixing hybrid and deterministic provenance (RT-11 residual) — the new `evaluator`/`sample` fields make a filtered variant easy when wanted.
