# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
mutante_client.py — Cliente LLM unificado de MUTANTE.

Antes acoplado exclusivamente a Vertex AI / Gemini; ahora es una fachada
delgada sobre la capa `providers`, que soporta Gemini (Vertex y AI Studio),
OpenAI y compatibles (OpenRouter/Groq/Together/Ollama/vLLM...) y Anthropic.

La firma pública se mantiene idéntica para no romper a los consumidores:
    call_target_async(prompt) -> str
    call_target_sync(prompt)  -> str
    TARGET_MODEL, AGENT_MODEL  (str, nombre de modelo resuelto)
    extract_text(resp)         (compat; para respuestas google-genai crudas)
    get_target_config()        (compat; config google-genai)
    get_genai_client()         (compat; cliente google si aplica, si no None)

Configuración por entorno: ver agent_mutante/engine/providers/__init__.py y
.env.example. En una instalación Vertex existente todo sigue funcionando sin
cambios (auto-detección por GOOGLE_CLOUD_PROJECT).
"""

import os

from dotenv import load_dotenv

from .providers import build_provider, GenerationConfig, blocked
from .providers.google_genai import GoogleGenAIProvider

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Proveedores por rol (singletons perezosos).
_target_provider = None
_agent_provider = None


def _target():
    global _target_provider
    if _target_provider is None:
        _target_provider = build_provider("TARGET")
    return _target_provider


def _agent():
    global _agent_provider
    if _agent_provider is None:
        _agent_provider = build_provider("AGENT")
    return _agent_provider


# Nombres de modelo resueltos, expuestos como constantes para etiquetado/telemetría.
TARGET_MODEL = _target().model
AGENT_MODEL = _agent().model
TARGET_PROVIDER = _target().name


# ── API pública (sin cambios de firma) ────────────────────────────────────────

async def call_target_async(prompt: str) -> str:
    """Llama al modelo objetivo de forma asíncrona."""
    return await _target().acomplete(prompt, GenerationConfig())


def call_target_sync(prompt: str) -> str:
    """Llama al modelo objetivo de forma síncrona (para tools ADK)."""
    return _target().complete(prompt, GenerationConfig())


# ── Compatibilidad hacia atrás (código legacy que asumía google-genai) ────────

def get_genai_client():
    """Devuelve el cliente google-genai subyacente si el target es Gemini; si no, None."""
    provider = _target()
    if isinstance(provider, GoogleGenAIProvider):
        return provider._get_client()
    return None


def get_target_config():
    """Config de generación google-genai (solo válida para backend Gemini)."""
    from google.genai import types
    return types.GenerateContentConfig(
        temperature=0.0,
        top_p=0.1,
        top_k=1,
        max_output_tokens=2048,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ],
    )


def extract_text(resp) -> str:
    """Extrae texto de una respuesta google-genai cruda (compat)."""
    return GoogleGenAIProvider._extract(resp)
