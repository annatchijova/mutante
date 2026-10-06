# Copyright 2026 Anna Tchijova
# Licensed under the Apache License, Version 2.0

"""
0DIN Curated Probe Source — 32 high-value probes with 34 retargetable variants each.

Syncs from a local JSON file (config/probes/0din_probes.json) containing
0DIN-disclosed jailbreaks with original attack prompt + variants.

Each base probe expands across substances/industries at runtime, similar to
ai-scanner's OdinProbeSource.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import (
    ProbeSource,
    register_source,
    NormalizedProbe,
    normalize_probes,
    needs_sync,
    write_sync_version,
    read_sync_version,
)


DEFAULT_0DIN_PATH = Path(__file__).parent.parent.parent / "config" / "probes" / "0din_probes.json"
DEFAULT_SUBSTANCES = ["sarin gas", "mdma", "ricin", "mustard gas"]


@register_source
class OdinProbeSource:
    name = "curated"
    category = "odin"
    SYNC_KEY = "odin:curated"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._cached_probes: Optional[List[NormalizedProbe]] = None
        self._file_path = Path(self.config.get("file_path", DEFAULT_0DIN_PATH))
        self._substances = self.config.get("substances", DEFAULT_SUBSTANCES)
        self.last_sync_error: Optional[str] = None

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        if "file_path" in config:
            self._file_path = Path(config["file_path"])
        if "substances" in config:
            self._substances = config["substances"]
        self._cached_probes = None

    def needs_sync(self) -> bool:
        return needs_sync(self.SYNC_KEY, self._file_path)

    def sync(self) -> Dict[str, Any]:
        if not self._file_path.exists():
            return {"success": False, "error": f"0DIN probes file not found: {self._file_path}"}

        try:
            data = json.loads(self._file_path.read_text())
            if not isinstance(data, dict) or "probes" not in data:
                return {"success": False, "error": "Invalid 0DIN probes format: missing 'probes' key"}

            probes_data = []
            variant_count = 0

            for probe_name, probe_json in data["probes"].items():
                prompts = probe_json.get("prompts", [])
                if not prompts:
                    continue

                # Base probe
                probes_data.append({
                    "name": probe_name,
                    "prompt": prompts[0] if prompts else "",
                    "prompts": prompts,
                    "detector": probe_json.get("detector"),
                    "variants": probe_json.get("variants", {}),
                })

                # Variants expansion (retargetable)
                variants = probe_json.get("variants", {})
                for industry_key, subindustries in variants.items():
                    for subindustry_key, variant_classes in subindustries.items():
                        for variant_class in variant_classes:
                            # Expand {substance} placeholder
                            for substance in self._substances:
                                expanded = variant_class.replace("{substance}", substance)
                                probes_data.append({
                                    "name": f"{probe_name}_variant",
                                    "prompt": expanded,
                                    "base_probe": probe_name,
                                    "industry": industry_key,
                                    "subindustry": subindustry_key,
                                    "substance": substance,
                                })
                                variant_count += 1

            normalized = normalize_probes(probes_data, self.category, self.name)
            self._cached_probes = normalized

            write_sync_version(self.SYNC_KEY, {
                "base_probes": len(data["probes"]),
                "total_probes": len(normalized),
                "variants": variant_count,
                "substances": self._substances,
            })

            return {
                "success": True,
                "base_probes": len(data["probes"]),
                "total_probes": len(normalized),
                "variants": variant_count,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def load(self) -> List[NormalizedProbe]:
        if self._cached_probes is not None:
            return self._cached_probes

        if self.needs_sync():
            result = self.sync()
            self.last_sync_error = None if result.get("success") else result.get("error", "sync failed")

        return self._cached_probes or []


@register_source
class OdinProbeSourceBaseOnly(OdinProbeSource):
    """0DIN probes without variant expansion (base prompts only)."""
    name = "curated_base"
    category = "odin"
    SYNC_KEY = "odin:curated_base"

    def sync(self) -> Dict[str, Any]:
        if not self._file_path.exists():
            return {"success": False, "error": f"0DIN probes file not found: {self._file_path}"}

        try:
            data = json.loads(self._file_path.read_text())
            probes_data = []
            for probe_name, probe_json in data.get("probes", {}).items():
                prompts = probe_json.get("prompts", [])
                if prompts:
                    probes_data.append({
                        "name": probe_name,
                        "prompt": prompts[0],
                        "prompts": prompts,
                        "detector": probe_json.get("detector"),
                    })

            normalized = normalize_probes(probes_data, self.category, self.name)
            self._cached_probes = normalized

            write_sync_version(self.SYNC_KEY, {
                "base_probes": len(normalized),
            })

            return {"success": True, "count": len(normalized)}

        except Exception as e:
            return {"success": False, "error": str(e)}