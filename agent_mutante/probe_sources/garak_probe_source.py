# Copyright 2026 Anna Tchijova
# Licensed under the Apache License, Version 2.0

"""
Garak Community Probe Source — wraps NVIDIA Garak as a probe source.

Garak provides 179 community probes across 35 vulnerability families aligned with
OWASP LLM Top 10. This source syncs the garak probe list and normalizes it for
MUTANTE campaigns.

Sync process:
  1. Runs `python -m garak --list_probes` to get available probes
  2. Optionally runs a quick probe to extract metadata (tags, description)
  3. Normalizes to MUTANTE's NormalizedProbe format
  4. Tracks sync version via probe list hash
"""

from __future__ import annotations

import json
import subprocess
import sys
import hashlib
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


@register_source
class GarakProbeSource:
    name = "community"
    category = "garak"
    SYNC_KEY = "garak:community"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._cached_probes: Optional[List[NormalizedProbe]] = None
        self._probe_list_hash: Optional[str] = None
        self.last_sync_error: Optional[str] = None

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self._cached_probes = None

    def _get_probe_list_hash(self) -> str:
        """Generate hash of available probe list for sync tracking."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "garak", "--list_probes"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return hashlib.sha256(result.stdout.encode()).hexdigest()[:16]
        except Exception:
            pass
        return "unknown"

    def needs_sync(self) -> bool:
        """Check if garak probe list has changed."""
        current_hash = self._get_probe_list_hash()
        version = read_sync_version(self.SYNC_KEY)
        if version is None:
            return True
        return version.get("probe_list_hash") != current_hash

    def sync(self) -> Dict[str, Any]:
        """Sync garak probe list and metadata."""
        try:
            # Get probe list
            result = subprocess.run(
                [sys.executable, "-m", "garak", "--list_probes"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return {"success": False, "error": f"garak --list_probes failed: {result.stderr}"}

            probe_names = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

            # Try to get metadata for each probe (optional, can be slow)
            probes_data = []
            for probe_name in probe_names:
                probe_info = {"name": probe_name}
                try:
                    # Get probe metadata via garak's internal API
                    meta_result = subprocess.run(
                        [
                            sys.executable, "-c",
                            "import garak.probes, sys; p = garak.probes.get(sys.argv[1]); print((p.__doc__ or '') if p else '')",
                            probe_name,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if meta_result.returncode == 0 and meta_result.stdout.strip():
                        probe_info["description"] = meta_result.stdout.strip()
                except Exception:
                    pass
                probes_data.append(probe_info)

            # Normalize
            normalized = normalize_probes(probes_data, self.category, self.name)

            # Cache
            self._cached_probes = normalized
            self._probe_list_hash = self._get_probe_list_hash()

            # Write sync version
            write_sync_version(self.SYNC_KEY, {
                "probe_list_hash": self._probe_list_hash,
                "count": len(normalized),
                "synced_at": Path(__file__).stat().st_mtime,  # approximate
            })

            return {
                "success": True,
                "count": len(normalized),
                "probe_list_hash": self._probe_list_hash,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def load(self) -> List[NormalizedProbe]:
        """Load normalized probes, syncing if needed."""
        if self._cached_probes is not None:
            return self._cached_probes

        if self.needs_sync():
            result = self.sync()
            self.last_sync_error = None if result.get("success") else result.get("error", "sync failed")

        if self._cached_probes is None:
            # Fallback: try to load from last sync
            version = read_sync_version(self.SYNC_KEY)
            if version and version.get("count", 0) > 0:
                # Reconstruct minimal probes from garak list
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "garak", "--list_probes"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        probe_names = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
                        probes_data = [{"name": n} for n in probe_names]
                        self._cached_probes = normalize_probes(probes_data, self.category, self.name)
                except Exception:
                    self._cached_probes = []

        return self._cached_probes or []


@register_source
class GarakProbeSourceExtended(GarakProbeSource):
    """Extended garak source that runs a quick probe to extract tags/metadata."""
    name = "community_extended"
    category = "garak"
    SYNC_KEY = "garak:community_extended"

    def sync(self) -> Dict[str, Any]:
        # First do base sync
        base_result = super().sync()
        if not base_result.get("success"):
            return base_result

        # Enrich with probe tags if available
        try:
            import garak.probes
            for probe in self._cached_probes or []:
                garak_probe = garak.probes.get(probe.metadata.get("name", probe.probe_id))
                if garak_probe:
                    probe.metadata["tags"] = getattr(garak_probe, "tags", [])
                    probe.metadata["description"] = getattr(garak_probe, "__doc__", "").strip() if garak_probe.__doc__ else ""
            write_sync_version(self.SYNC_KEY, {
                "probe_list_hash": self._probe_list_hash,
                "count": len(self._cached_probes or []),
                "enriched": True,
            })
        except Exception:
            pass

        return {"success": True, "count": len(self._cached_probes or []), "enriched": True}