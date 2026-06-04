# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
mutante_client.py — Cliente unificado de Google GenAI para todo MUTANTE.
ÚNICA fuente de verdad para la conexión a Vertex AI.
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

PROJECT_ID   = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION     = os.getenv("VERTEX_AI_LOCATION", "us-central1")
TARGET_MODEL = os.getenv("TARGET_MODEL", "gemini-3-flash")
AGENT_MODEL  = os.getenv("AGENT_MODEL", TARGET_MODEL)

_client = None
_client_init_done = False


def get_genai_client():
    """Inicializa y retorna el cliente unificado google-genai. Singleton."""
    global _client, _client_init_done
    if _client_init_done:
        return _client
    _client_init_done = True
    
    if not PROJECT_ID:
        return None
    
    try:
        from google import genai
        _client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"[!] Error inicializando GenAI client: {e}", file=sys.stderr)
        _client = None
    return _client


def get_target_config():
    """Retorna la configuración de generación estándar para el modelo objetivo."""
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
    """
    Extrae texto de respuesta google-genai de forma segura.
    Maneja safety blocks, candidatos vacíos, y errores.
    """
    try:
        candidates = getattr(resp, "candidates", None)
        if not candidates:
            return "BLOCKED_OR_ERROR: empty candidates (possible safety block)"
        
        finish = getattr(candidates[0], "finish_reason", None)
        finish_name = str(getattr(finish, "name", finish) or "").upper()
        if finish_name in {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}:
            return f"BLOCKED_OR_ERROR: finish_reason={finish_name}"
        
        text = resp.text
        return text if text else "BLOCKED_OR_ERROR: empty text"
    except Exception as e:
        return f"BLOCKED_OR_ERROR: extraction failed: {e}"


async def call_target_async(prompt: str) -> str:
    """Llama al modelo objetivo de forma asíncrona."""
    client = get_genai_client()
    if client is None:
        return "BLOCKED_OR_ERROR: client not initialized"
    
    try:
        resp = await client.aio.models.generate_content(
            model=TARGET_MODEL,
            contents=prompt,
            config=get_target_config(),
        )
        return extract_text(resp)
    except Exception as e:
        return f"BLOCKED_OR_ERROR: {e}"


def call_target_sync(prompt: str) -> str:
    """Llama al modelo objetivo de forma síncrona (para tools ADK)."""
    client = get_genai_client()
    if client is None:
        return "BLOCKED_OR_ERROR: client not initialized"
    
    try:
        resp = client.models.generate_content(
            model=TARGET_MODEL,
            contents=prompt,
            config=get_target_config(),
        )
        return extract_text(resp)
    except Exception as e:
        return f"BLOCKED_OR_ERROR: {e}"
