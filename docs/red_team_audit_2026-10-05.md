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
