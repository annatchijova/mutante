# Copyright 2026 Anna Tchijova
# Licensed under the Apache License, Version 2.0

"""
Generic Probe Source — Load probes from CSV, JSON, or JSONL files.

Supports:
  - CSV with columns: prompt, [id, category, tags, ...]
  - JSON with {probes: [{prompt, id, ...}, ...]} or array format
  - JSONL with one probe per line

Automatically detects format and normalizes to MUTANTE's NormalizedProbe.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Some corpora contain very long prompt fields; raise the parser limit.
csv.field_size_limit(1024 * 1024 * 1024)

from . import (
    ProbeSource,
    register_source,
    NormalizedProbe,
    normalize_probes,
    needs_sync,
    write_sync_version,
    read_sync_version,
)


@register_source
class GenericProbeSource:
    name = "generic"
    category = "custom"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._cached_probes: Optional[List[NormalizedProbe]] = None
        self._file_path = Path(self.config.get("file_path", ""))
        self._prompt_column = self.config.get("prompt_column", "prompt")
        self._id_column = self.config.get("id_column", "id")
        self._category_column = self.config.get("category_column", "category")
        self._filter_column = self.config.get("filter_column")
        self._filter_value = self.config.get("filter_value")
        self._limit = self.config.get("limit")
        self.last_sync_error: Optional[str] = None

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        if "file_path" in config:
            self._file_path = Path(config["file_path"])
        if "prompt_column" in config:
            self._prompt_column = config["prompt_column"]
        if "id_column" in config:
            self._id_column = config["id_column"]
        if "category_column" in config:
            self._category_column = config["category_column"]
        if "filter_column" in config:
            self._filter_column = config["filter_column"]
        if "filter_value" in config:
            self._filter_value = config["filter_value"]
        if "limit" in config:
            self._limit = config["limit"]
        self._cached_probes = None

    @property
    def SYNC_KEY(self) -> str:
        return f"custom:{self.name}"

    def needs_sync(self) -> bool:
        return needs_sync(self.SYNC_KEY, self._file_path)

    def _load_csv(self) -> List[Dict[str, Any]]:
        probes = []
        with open(self._file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._filter_column and row.get(self._filter_column) != self._filter_value:
                    continue
                probes.append(dict(row))
                if self._limit and len(probes) >= self._limit:
                    break
        return probes

    def _load_json(self) -> List[Dict[str, Any]]:
        data = json.loads(self._file_path.read_text())
        if isinstance(data, dict) and "probes" in data:
            return data["probes"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("JSON must be an array or object with 'probes' key")

    def _load_jsonl(self) -> List[Dict[str, Any]]:
        probes = []
        with open(self._file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                probes.append(json.loads(line))
                if self._limit and len(probes) >= self._limit:
                    break
        return probes

    def sync(self) -> Dict[str, Any]:
        if not self._file_path.exists():
            return {"success": False, "error": f"Probe file not found: {self._file_path}"}

        try:
            suffix = self._file_path.suffix.lower()
            if suffix == ".csv":
                raw_probes = self._load_csv()
            elif suffix == ".json":
                raw_probes = self._load_json()
            elif suffix == ".jsonl":
                raw_probes = self._load_jsonl()
            else:
                return {"success": False, "error": f"Unsupported file format: {suffix}"}

            # Remap configured columns to the canonical keys normalize_probes expects
            remapped = []
            for row in raw_probes:
                row = dict(row)
                if self._prompt_column != "prompt" and self._prompt_column in row and "prompt" not in row:
                    row["prompt"] = row[self._prompt_column]
                if self._id_column != "id" and self._id_column in row and "id" not in row:
                    row["id"] = row[self._id_column]
                remapped.append(row)

            # Normalize
            category = self.config.get("category", self.category)
            source = self.config.get("source", self.name)
            normalized = normalize_probes(remapped, category, source)

            # Apply limit after normalization if needed
            if self._limit and len(normalized) > self._limit:
                normalized = normalized[:self._limit]

            self._cached_probes = normalized

            write_sync_version(self.SYNC_KEY, {
                "file": str(self._file_path),
                "count": len(normalized),
                "format": suffix,
            })

            return {"success": True, "count": len(normalized)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def load(self) -> List[NormalizedProbe]:
        if self._cached_probes is not None:
            return self._cached_probes

        if self.needs_sync():
            result = self.sync()
            self.last_sync_error = None if result.get("success") else result.get("error", "sync failed")

        return self._cached_probes or []


# Pre-configured sources for common corpora
@register_source
class HarmBenchProbeSource(GenericProbeSource):
    name = "harmbench"
    category = "harmbench"
    SYNC_KEY = "harmbench:default"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            "file_path": str(Path(__file__).parent.parent.parent / "harmbench_behaviors.csv"),
            "prompt_column": "Behavior",
            "id_column": "BehaviorID",
            "category": "harmbench",
            "source": "harmbench",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)


@register_source
class WildChatProbeSource(GenericProbeSource):
    name = "wildchat"
    category = "wildchat"
    SYNC_KEY = "wildchat:default"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            "file_path": str(Path(__file__).parent.parent.parent / "wildchat_1m.jsonl"),
            "prompt_column": "prompt",
            "id_column": "id",
            "category": "wildchat",
            "source": "wildchat",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)


@register_source
class AgenticSecurityProbeSource(GenericProbeSource):
    name = "agentic_security"
    category = "agentic_security"
    SYNC_KEY = "agentic_security:default"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = {
            "file_path": str(Path(__file__).parent.parent.parent / "agentic_security_prompts.json"),
            "prompt_column": "prompt",
            "id_column": "id",
            "category": "agentic_security",
            "source": "agentic_security",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)


# Legacy jailbreak CSV corpora (pre-registry DATASET_FILES in run_campaign.py)
def _legacy_jailbreak_source(cls_name: str, file_name: str, source_name: str, filter_jailbreak: bool) -> type:
    """Build a GenericProbeSource subclass bound to a legacy jailbreak CSV."""
    @register_source
    class _Source(GenericProbeSource):
        name = source_name
        category = "jailbreaks"
        SYNC_KEY = f"jailbreaks:{source_name}"

        def __init__(self, config: Optional[Dict[str, Any]] = None):
            default_config = {
                "file_path": str(Path(__file__).parent.parent.parent / file_name),
                "prompt_column": "prompt",
                "category": "jailbreaks",
                "source": source_name,
            }
            if filter_jailbreak:
                default_config["filter_column"] = "type"
                default_config["filter_value"] = "jailbreak"
            if config:
                default_config.update(config)
            super().__init__(default_config)

    _Source.__name__ = cls_name
    _Source.__qualname__ = cls_name
    return _Source


# master_11k uses successful_jailbreak/unsuccessful_jailbreak labels, not "jailbreak";
# both are attack prompts, so it loads unfiltered.
_legacy_jailbreak_source("JailbreakMaster11KProbeSource", "jailbreaks_dataset_master_11k.csv", "master_11k", filter_jailbreak=False)
_legacy_jailbreak_source("JailbreakFinalProbeSource", "jailbreaks_dataset_final.csv", "final", filter_jailbreak=True)
_legacy_jailbreak_source("JailbreakMasterProbeSource", "jailbreaks_dataset_master.csv", "master", filter_jailbreak=True)
_legacy_jailbreak_source("JailbreakEnrichedProbeSource", "jailbreaks_dataset_master_enriched.csv", "enriched", filter_jailbreak=True)