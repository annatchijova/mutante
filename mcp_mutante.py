#!/usr/bin/env python3
# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0 (the "License");

import os
import sys
import json
import base64
import codecs
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mcp.server.fastmcp import FastMCP
from agent_mutante.engine.mutante_semiotic_evaluator import evaluate_bypass

# Elastic Cloud opcional
CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID", "")
API_KEY = os.getenv("ELASTIC_API_KEY", "")
es = None

if CLOUD_ID and API_KEY:
    try:
        from elasticsearch import Elasticsearch
        _es_candidate = Elasticsearch(cloud_id=CLOUD_ID, api_key=API_KEY)
        if _es_candidate.ping():
            es = _es_candidate
            print("[+] Conectado a Elastic Cloud.", file=sys.stderr)
        else:
            print("[-] Elastic Cloud offline.", file=sys.stderr)
    except Exception as e:
        print(f"[-] Error Elastic: {e}", file=sys.stderr)
else:
    print("[-] Falta config Elastic. Indexación desactivada.", file=sys.stderr)

# Cargar dataset con pandas en vez de datasets
import pandas as pd

DATASET_PATH = os.path.join(BASE_DIR, "jailbreaks_dataset_master.csv")
dataset_rows = []
dataset_idx = 0

if os.path.exists(DATASET_PATH):
    try:
        df = pd.read_csv(DATASET_PATH)
        if "prompt" in df.columns:
            dataset_rows = df["prompt"].dropna().tolist()
        print(f"[+] Dataset cargado: {len(dataset_rows)} prompts", file=sys.stderr)
    except Exception as e:
        print(f"[-] Error cargando dataset: {e}", file=sys.stderr)
else:
    print(f"[!] Dataset no encontrado: {DATASET_PATH}", file=sys.stderr)

mcp = FastMCP("Mutante-RedTeam")

@mcp.tool()
def generate_mutated_attack(mutation_type: str) -> str:
    """Extrae un prompt del dataset y le aplica la mutación solicitada."""
    global dataset_idx
    if not dataset_rows:
        return "ERROR: No dataset loaded"
    
    if dataset_idx >= len(dataset_rows):
        dataset_idx = 0
    
    base_prompt = dataset_rows[dataset_idx]
    dataset_idx += 1
    
    mutation_lower = mutation_type.lower()
    if mutation_lower == "base64":
        return base64.b64encode(base_prompt.encode("utf-8")).decode("utf-8")
    elif mutation_lower == "rot13":
        return codecs.encode(base_prompt, "rot_13")
    elif mutation_lower in ("mirror", "espejo"):
        return base_prompt[::-1]
    
    return base_prompt

@mcp.tool()
def evaluate_bayesian_breach(prompt_id: str, mutation_type: str, agent_response: str) -> str:
    """Invoca la evaluación determinista para el output del modelo."""
    result = evaluate_bypass(
        prompt_id=prompt_id,
        mutation_type=mutation_type,
        response_text=agent_response,
    )
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool()
def indexar_brecha_en_elastic(breach_data: str) -> str:
    """Envía el payload de telemetría forense a Elastic Cloud."""
    if es is None:
        return "Elastic indexing skipped: cliente no configurado u offline."
    try:
        document = json.loads(breach_data)
        result = es.index(index="mutante-audits", document=document)
        return f"OK. ID: {result['_id']}"
    except Exception as e:
        return f"Error en Elastic index: {e}"

if __name__ == "__main__":
    print("[*] Servidor FastMCP de MUTANTE inicializado.", file=sys.stderr)
    mcp.run()
