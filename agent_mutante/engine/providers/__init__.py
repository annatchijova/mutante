# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
providers — Capa multi-proveedor de MUTANTE.

Resuelve, a partir de variables de entorno, qué backend LLM usar para cada
rol del pipeline (`target`, `agent`, `evaluator`) y devuelve un `LLMProvider`.

Formas de configurar un modelo (de mayor a menor prioridad):

  1. Prefijo `proveedor/modelo` en la variable de modelo:
         TARGET_MODEL="openai/gpt-4o"
         TARGET_MODEL="anthropic/claude-3-5-sonnet-latest"
         TARGET_MODEL="ollama/llama3.1"           (endpoint local)
         TARGET_MODEL="vertex/gemini-3-flash"
         TARGET_MODEL="gemini/gemini-2.5-flash"   (Google AI Studio, con API key)

  2. Variable explícita de proveedor:
         TARGET_PROVIDER="openai"   TARGET_MODEL="gpt-4o"

  3. Auto-detección (compatibilidad con la instalación Vertex original):
         si GOOGLE_CLOUD_PROJECT está definido → Vertex/Gemini.

El resto de MUTANTE sigue llamando a `mutante_client.call_target_async/sync`,
que ahora delega en esta capa sin cambiar su firma.
"""

import os

from .base import GenerationConfig, LLMProvider, blocked, BLOCKED_PREFIX
from .google_genai import GoogleGenAIProvider
from .openai_compatible import OpenAICompatibleProvider, DEFAULT_BASE_URL as OPENAI_BASE
from .anthropic import AnthropicProvider

__all__ = [
    "GenerationConfig", "LLMProvider", "blocked", "BLOCKED_PREFIX",
    "GoogleGenAIProvider", "OpenAICompatibleProvider", "AnthropicProvider",
    "build_provider", "resolve_spec",
]

# Alias de prefijo → (familia, base_url por defecto).
# La familia elige la clase; base_url solo aplica a la familia openai-compatible.
_ALIASES = {
    "vertex":            ("vertex", None),
    "gemini-vertex":     ("vertex", None),
    "gemini":            ("gemini", None),
    "google":            ("gemini", None),
    "aistudio":          ("gemini", None),
    "openai":            ("openai", OPENAI_BASE),
    "gpt":               ("openai", OPENAI_BASE),
    "azure":             ("openai", None),      # requiere OPENAI_BASE_URL propio
    "openai-compatible": ("openai", None),
    "compat":            ("openai", None),
    "openrouter":        ("openai", "https://openrouter.ai/api/v1"),
    "groq":              ("openai", "https://api.groq.com/openai/v1"),
    "together":          ("openai", "https://api.together.xyz/v1"),
    "fireworks":         ("openai", "https://api.fireworks.ai/inference/v1"),
    "deepseek":          ("openai", "https://api.deepseek.com/v1"),
    "ollama":            ("openai", "http://localhost:11434/v1"),
    "vllm":              ("openai", "http://localhost:8000/v1"),
    "lmstudio":          ("openai", "http://localhost:1234/v1"),
    "anthropic":         ("anthropic", None),
    "claude":            ("anthropic", None),
}


def _env(role: str, suffix: str, default: str = "") -> str:
    """Lee VAR específica de rol y cae a la global. role='TARGET' → TARGET_MODEL."""
    return os.getenv(f"{role}_{suffix}", os.getenv(suffix, default))


def resolve_spec(model_spec: str) -> tuple[str, str, str | None]:
    """Descompone `proveedor/modelo` → (familia, modelo, base_url_default).

    Si no hay prefijo reconocido, familia="" (se decidirá por otras señales).
    """
    if "/" in model_spec:
        head, tail = model_spec.split("/", 1)
        alias = _ALIASES.get(head.lower())
        if alias:
            family, base = alias
            return family, tail, base
    # sin prefijo: inferir por nombre de modelo
    low = model_spec.lower()
    if low.startswith(("gpt-", "gpt4", "o1", "o3", "o4", "chatgpt")):
        return "openai", model_spec, OPENAI_BASE
    if low.startswith("claude"):
        return "anthropic", model_spec, None
    return "", model_spec, None


def build_provider(role: str = "TARGET") -> LLMProvider:
    """Construye el proveedor para un rol ('TARGET', 'AGENT', 'EVALUATOR').

    Nunca lanza: si algo falta, devuelve un proveedor cuyo `.available()` es
    falso y cuyas llamadas devuelven `blocked(...)`.
    """
    role = role.upper()

    # 1) modelo (con posible prefijo proveedor/)
    if role == "TARGET":
        model_spec = _env("TARGET", "MODEL", "gemini-3-flash")
    elif role == "AGENT":
        model_spec = _env("AGENT", "MODEL", os.getenv("TARGET_MODEL", "gemini-3-flash"))
    else:  # EVALUATOR
        model_spec = _env("EVALUATOR", "MODEL", "gemini-2.5-flash")

    family, model, base_default = resolve_spec(model_spec)

    # 2) proveedor explícito (gana sobre inferencia por nombre, pierde vs prefijo)
    explicit = _env(role, "PROVIDER", "").lower()
    if explicit and not (family and "/" in model_spec):
        alias = _ALIASES.get(explicit)
        if alias:
            family, base_default = alias[0], alias[1] or base_default

    # 3) auto-detección final
    if not family:
        if os.getenv("GOOGLE_CLOUD_PROJECT"):
            family = "vertex"
        elif os.getenv("OPENAI_API_KEY"):
            family = "openai"; base_default = OPENAI_BASE
        elif os.getenv("ANTHROPIC_API_KEY"):
            family = "anthropic"
        elif os.getenv("GEMINI_API_KEY"):
            family = "gemini"
        else:
            family = "vertex"  # compatibilidad histórica

    # 4) instanciar
    if family == "vertex":
        return GoogleGenAIProvider(
            model=model, vertex=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
        )
    if family == "gemini":
        return GoogleGenAIProvider(
            model=model, vertex=False,
            api_key=os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        )
    if family == "anthropic":
        return AnthropicProvider(
            model=model,
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        )
    # familia == "openai" (OpenAI + compatibles)
    base_url = os.getenv("OPENAI_BASE_URL", base_default or OPENAI_BASE)
    return OpenAICompatibleProvider(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "")),
        base_url=base_url,
        organization=os.getenv("OPENAI_ORG", ""),
    )
