# Copyright 2026 Anna Tchijova
# Licensed under the Apache License, Version 2.0

"""
Probe Source Registry — Pluggable adversarial corpus sources.

Pattern derived from 0din/ai-scanner's ProbeSourceRegistry (Ruby).
Each source implements:
  - name: unique identifier
  - category: logical grouping (garak, odin, harmbench, custom)
  - sync() -> dict: pulls probes, returns {success: bool, count: int, metadata: dict}
  - load() -> list[dict]: returns normalized probes for the campaign
  - needs_sync() -> bool: whether upstream data changed

Sources are registered at import time via @register_source decorator.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Protocol
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib
import time


class ProbeSource(Protocol):
    """Protocol for a probe source."""

    name: str
    category: str

    def needs_sync(self) -> bool: ...
    def sync(self) -> Dict[str, Any]: ...
    def load(self) -> List[Dict[str, Any]]: ...


@dataclass
class ProbeSourceMeta:
    """Registry entry for a probe source."""
    source_class: type
    instance: Optional[ProbeSource] = None
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class ProbeSourceRegistry:
    """Thread-safe registry for probe sources."""

    _sources: Dict[str, ProbeSourceMeta] = {}
    _lock = threading.RLock()
    _initialized = False

    @classmethod
    def register(cls, source_class: type) -> type:
        """Decorator to register a probe source class."""
        with cls._lock:
            instance = source_class()
            key = f"{instance.category}:{instance.name}"
            if key in cls._sources:
                raise ValueError(f"Probe source already registered: {key}")
            cls._sources[key] = ProbeSourceMeta(source_class=source_class, instance=instance)
        return source_class

    @classmethod
    def get(cls, category: str, name: str) -> Optional[ProbeSource]:
        """Get a probe source instance by category and name."""
        with cls._lock:
            key = f"{category}:{name}"
            meta = cls._sources.get(key)
            return meta.instance if meta and meta.enabled else None

    @classmethod
    def get_all(cls, enabled_only: bool = True, category: Optional[str] = None) -> List[ProbeSource]:
        """Get all registered probe sources, optionally filtered."""
        with cls._lock:
            sources = []
            for key, meta in cls._sources.items():
                if enabled_only and not meta.enabled:
                    continue
                if category and not key.startswith(f"{category}:"):
                    continue
                if meta.instance:
                    sources.append(meta.instance)
            return sources

    @classmethod
    def enable(cls, category: str, name: str) -> bool:
        with cls._lock:
            key = f"{category}:{name}"
            if key in cls._sources:
                cls._sources[key].enabled = True
                return True
            return False

    @classmethod
    def disable(cls, category: str, name: str) -> bool:
        with cls._lock:
            key = f"{category}:{name}"
            if key in cls._sources:
                cls._sources[key].enabled = False
                return True
            return False

    @classmethod
    def list_registered(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return [
                {
                    "category": meta.instance.category if meta.instance else key.split(":")[0],
                    "name": meta.instance.name if meta.instance else key.split(":")[1],
                    "enabled": meta.enabled,
                    "config": meta.config,
                }
                for key, meta in cls._sources.items()
            ]

    @classmethod
    def configure(cls, category: str, name: str, config: Dict[str, Any]) -> bool:
        with cls._lock:
            key = f"{category}:{name}"
            if key in cls._sources:
                cls._sources[key].config.update(config)
                if cls._sources[key].instance and hasattr(cls._sources[key].instance, "configure"):
                    cls._sources[key].instance.configure(config)
                return True
            return False


def register_source(source_class: type) -> type:
    """Convenience decorator for probe source registration."""
    return ProbeSourceRegistry.register(source_class)


# Auto-import submodules to trigger registration
def _auto_import_submodules():
    """Import all probe source modules to register them."""
    import importlib
    for mod_name in ("garak_probe_source", "odin_probe_source", "generic_probe_source", "mutation_source"):
        try:
            importlib.import_module(f".{mod_name}", __name__)
        except ImportError:
            pass


# --- Sync version tracking ---

SYNC_VERSION_DIR = Path(__file__).parent.parent.parent / "config" / "sync_versions"
SYNC_VERSION_DIR.mkdir(parents=True, exist_ok=True)


def _sync_version_path(sync_key: str) -> Path:
    return SYNC_VERSION_DIR / f"{sync_key.replace(':', '_')}.json"


def read_sync_version(sync_key: str) -> Optional[Dict[str, Any]]:
    path = _sync_version_path(sync_key)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def write_sync_version(sync_key: str, data: Dict[str, Any]) -> None:
    path = _sync_version_path(sync_key)
    data.setdefault("synced_at", time.time())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def needs_sync(sync_key: str, source_file: Optional[Path] = None) -> bool:
    """Check if a source needs sync based on version file and optional source file mtime."""
    version = read_sync_version(sync_key)
    if version is None:
        return True
    if source_file and source_file.exists():
        source_mtime = source_file.stat().st_mtime
        if source_mtime > version.get("synced_at", 0):
            return True
    return False


# --- Normalized probe format ---

@dataclass
class NormalizedProbe:
    """Canonical probe representation used by the campaign runner."""
    prompt: str
    probe_id: str
    category: str
    source: str
    mutation_families: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "probe_id": self.probe_id,
            "category": self.category,
            "source": self.source,
            "mutation_families": self.mutation_families,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedProbe":
        return cls(
            prompt=data["prompt"],
            probe_id=data["probe_id"],
            category=data["category"],
            source=data["source"],
            mutation_families=data.get("mutation_families", []),
            metadata=data.get("metadata", {}),
        )


def normalize_probes(raw_probes: List[Dict[str, Any]], category: str, source: str) -> List[NormalizedProbe]:
    """Convert raw probe dicts to NormalizedProbe list."""
    normalized = []
    for i, probe in enumerate(raw_probes):
        prompt = probe.get("prompt") or probe.get("text") or probe.get("content")
        if not prompt or not isinstance(prompt, str):
            continue
        probe_id = probe.get("id") or probe.get("name") or f"{category}_{source}_{i}"
        mutation_families = probe.get("mutation_families", [])
        metadata = {k: v for k, v in probe.items() if k not in ("prompt", "text", "content", "id", "name", "mutation_families")}
        normalized.append(NormalizedProbe(
            prompt=prompt.strip(),
            probe_id=str(probe_id),
            category=category,
            source=source,
            mutation_families=mutation_families,
            metadata=metadata,
        ))
    return normalized


# Ensure registration happens on import
_auto_import_submodules()