# Copyright 2026 Anna Tchijova
# Licensed under the Apache License, Version 2.0

"""
Mutation Source Registry — Pluggable mutation transformation families.

Allows registering custom mutation engines beyond the built-in 5 families
(rot13, base64_encode, mirror, scramble, zigzag).
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass


class MutationEngine(Protocol):
    """Protocol for a mutation engine."""

    name: str
    description: str

    def apply(self, text: str) -> str: ...
    def get_mutations(self) -> List[str]: ...


@dataclass
class MutationSourceMeta:
    engine_class: type
    instance: Optional[MutationEngine] = None
    enabled: bool = True
    config: Dict[str, Any] = None


class MutationSourceRegistry:
    """Thread-safe registry for mutation engines."""

    _sources: Dict[str, MutationSourceMeta] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, engine_class: type) -> type:
        with cls._lock:
            instance = engine_class()
            if instance.name in cls._sources:
                raise ValueError(f"Mutation engine already registered: {instance.name}")
            cls._sources[instance.name] = MutationSourceMeta(
                engine_class=engine_class,
                instance=instance,
                config={},
            )
        return engine_class

    @classmethod
    def get(cls, name: str) -> Optional[MutationEngine]:
        with cls._lock:
            meta = cls._sources.get(name)
            return meta.instance if meta and meta.enabled else None

    @classmethod
    def get_all(cls, enabled_only: bool = True) -> List[MutationEngine]:
        with cls._lock:
            return [
                meta.instance for meta in cls._sources.values()
                if meta.instance and (not enabled_only or meta.enabled)
            ]

    @classmethod
    def get_names(cls, enabled_only: bool = True) -> List[str]:
        with cls._lock:
            return [
                name for name, meta in cls._sources.items()
                if meta.instance and (not enabled_only or meta.enabled)
            ]

    @classmethod
    def list_registered(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return [
                {"name": name, "enabled": meta.enabled, "config": meta.config}
                for name, meta in cls._sources.items()
            ]

    @classmethod
    def enable(cls, name: str) -> bool:
        with cls._lock:
            if name in cls._sources:
                cls._sources[name].enabled = True
                return True
            return False

    @classmethod
    def disable(cls, name: str) -> bool:
        with cls._lock:
            if name in cls._sources:
                cls._sources[name].enabled = False
                return True
            return False

    @classmethod
    def configure(cls, name: str, config: Dict[str, Any]) -> bool:
        with cls._lock:
            if name in cls._sources:
                cls._sources[name].config = config
                if cls._sources[name].instance and hasattr(cls._sources[name].instance, "configure"):
                    cls._sources[name].instance.configure(config)
                return True
            return False


def register_mutation(engine_class: type) -> type:
    return MutationSourceRegistry.register(engine_class)


# --- Built-in mutation engines ---

@register_mutation
class Rot13Mutation:
    name = "rot13"
    description = "ROT13 substitution cipher (involutory)"

    def apply(self, text: str) -> str:
        result = []
        for char in text:
            if "A" <= char <= "Z":
                result.append(chr((ord(char) - ord("A") + 13) % 26 + ord("A")))
            elif "a" <= char <= "z":
                result.append(chr((ord(char) - ord("a") + 13) % 26 + ord("a")))
            else:
                result.append(char)
        return "".join(result)

    def get_mutations(self) -> List[str]:
        return [self.name]


@register_mutation
class Base64Mutation:
    name = "base64_encode"
    description = "Base64 encoding"

    import base64

    def apply(self, text: str) -> str:
        return self.base64.b64encode(text.encode("utf-8")).decode("utf-8")

    def get_mutations(self) -> List[str]:
        return [self.name]


@register_mutation
class MirrorMutation:
    name = "mirror"
    description = "Word-level character reversal"

    def apply(self, text: str) -> str:
        return " ".join(word[::-1] for word in text.split())

    def get_mutations(self) -> List[str]:
        return [self.name]


@register_mutation
class ScrambleMutation:
    name = "scramble"
    description = "Middle-character scramble (deterministic per word)"

    import random

    def apply(self, text: str) -> str:
        def _scramble_word(word: str) -> str:
            if len(word) > 3:
                middle = list(word[1:-1])
                self.random.Random(word).shuffle(middle)
                return word[0] + "".join(middle) + word[-1]
            return word
        return " ".join(_scramble_word(w) for w in text.split())

    def get_mutations(self) -> List[str]:
        return [self.name]


@register_mutation
class ZigzagMutation:
    name = "zigzag"
    description = "Alternating case per character"

    def apply(self, text: str) -> str:
        result = ""
        upper = True
        for char in text:
            if char.isalpha():
                result += char.upper() if upper else char.lower()
                upper = not upper
            else:
                result += char
        return result

    def get_mutations(self) -> List[str]:
        return [self.name]


# --- Composite mutation engines ---

@register_mutation
class CompositeMutation:
    """Applies multiple mutations in sequence."""
    name = "composite"
    description = "Sequential composition of multiple mutations"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mutation_sequence = self.config.get("sequence", ["rot13", "base64_encode"])

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self.mutation_sequence = self.config.get("sequence", self.mutation_sequence)

    def apply(self, text: str) -> str:
        for mutation_name in self.mutation_sequence:
            if mutation_name == self.name:
                continue
            engine = MutationSourceRegistry.get(mutation_name)
            if engine:
                text = engine.apply(text)
        return text

    def get_mutations(self) -> List[str]:
        return self.mutation_sequence


@register_mutation
class UnicodeObfuscationMutation:
    """Unicode tag character injection (invisible to humans, visible to models)."""
    name = "unicode_tags"
    description = "Inject Unicode tag characters (U+E0000-U+E007F) — invisible HTML injection"

    TAG_BASE = 0xE0000

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.density = self.config.get("density", 0.1)  # fraction of chars to tag

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self.density = self.config.get("density", self.density)

    def _char_to_tag(self, char: str) -> str:
        if "a" <= char <= "z":
            return chr(self.TAG_BASE + ord(char) - ord("a") + 0x61)
        elif "A" <= char <= "Z":
            return chr(self.TAG_BASE + ord(char) - ord("A") + 0x41)
        elif "0" <= char <= "9":
            return chr(self.TAG_BASE + ord(char) - ord("0") + 0x30)
        return char

    def apply(self, text: str) -> str:
        import random
        rng = random.Random(text)
        result = []
        for char in text:
            if char.isalnum() and rng.random() < self.density:
                result.append(self._char_to_tag(char))
            result.append(char)
        return "".join(result)

    def get_mutations(self) -> List[str]:
        return [self.name]


@register_mutation
class HomoglyphMutation:
    """Replace ASCII chars with visually similar Unicode homoglyphs."""
    name = "homoglyph"
    description = "Homoglyph substitution (Cyrillic, Greek lookalikes)"

    HOMOGLYPH_MAP = {
        "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "y": "у",
        "x": "х", "i": "і", "j": "ј", "k": "к", "l": "ӏ", "m": "м",
        "n": "п", "s": "ѕ", "u": "υ", "w": "ѡ", "z": "ᴢ",
        "A": "А", "E": "Е", "O": "О", "P": "Р", "C": "С", "Y": "У",
        "X": "Х", "I": "І", "J": "Ј", "K": "К", "M": "М", "N": "Н",
        "S": "Ѕ", "T": "Т", "B": "В", "H": "Н",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.probability = self.config.get("probability", 0.3)

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self.probability = self.config.get("probability", self.probability)

    def apply(self, text: str) -> str:
        import random
        rng = random.Random(text)
        result = []
        for char in text:
            if char in self.HOMOGLYPH_MAP and rng.random() < self.probability:
                result.append(self.HOMOGLYPH_MAP[char])
            else:
                result.append(char)
        return "".join(result)

    def get_mutations(self) -> List[str]:
        return [self.name]