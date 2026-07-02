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
providers/base.py — Contrato común de proveedores LLM para MUTANTE.

MUTANTE dejó de depender exclusivamente de Vertex AI / Gemini. Todo proveedor
(Gemini, OpenAI, Anthropic, endpoints OpenAI-compatibles locales/remotos)
implementa la misma interfaz `LLMProvider` y devuelve texto plano o el
sentinel `BLOCKED_OR_ERROR:` que el resto del motor ya sabe interpretar.
"""

from dataclasses import dataclass

# Sentinel reconocido por todo el pipeline (evaluador, quality gate, sinks).
# Se mantiene idéntico al que producía el cliente Vertex original para no
# romper la lógica de detección de bloqueos/errores aguas abajo.
BLOCKED_PREFIX = "BLOCKED_OR_ERROR"


def blocked(reason: str) -> str:
    """Construye una respuesta-sentinel uniforme."""
    return f"{BLOCKED_PREFIX}: {reason}"


@dataclass
class GenerationConfig:
    """Parámetros de generación neutrales respecto del proveedor.

    Cada proveedor traduce estos campos a su propio esquema. Los valores por
    defecto son deterministas (temperatura 0) para reproducibilidad forense.
    """
    temperature: float = 0.0
    top_p: float = 0.1
    top_k: int = 1
    max_output_tokens: int = 2048
    # response_json fuerza salida JSON cuando el proveedor lo soporta (juez).
    response_json: bool = False


class LLMProvider:
    """Interfaz mínima que implementa cada backend.

    Contrato:
      - `complete`/`acomplete` devuelven SIEMPRE un str. Ante fallo, safety
        block o credenciales ausentes devuelven `blocked(reason)` en lugar de
        lanzar excepción, para que la campaña continúe sin abortar.
      - `available()` permite chequear configuración antes de correr.
    """

    #: identificador corto del backend ("vertex", "openai", ...)
    name = "base"

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.options = kwargs

    # ── introspección ─────────────────────────────────────────────────────
    def available(self) -> tuple[bool, str]:
        """(ok, motivo). ok=False si falta credencial/dependencia."""
        return True, ""

    def describe(self) -> str:
        return f"{self.name}:{self.model}"

    # ── generación ────────────────────────────────────────────────────────
    def complete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        raise NotImplementedError

    async def acomplete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        """Por defecto delega en la versión síncrona en un thread.

        Los proveedores con soporte async nativo (HTTP vía aiohttp, google-genai
        aio) sobreescriben esto para evitar el thread pool.
        """
        import asyncio

        cfg = config or GenerationConfig()
        return await asyncio.to_thread(self.complete, prompt, cfg)
