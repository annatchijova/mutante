#!/usr/bin/env python3
"""
test_vertex_gemini.py — Test de conexión con google-genai (migrado desde vertexai).
"""

import os
import re
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")
MODEL_NAME = os.getenv("TARGET_MODEL", "gemini-3.1-pro-preview")

from google import genai
from google.genai import types

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

system_instruction = """
You are an expert Python engineer.
RULES:
1. NEVER invent model names, API versions, or packages that don't exist.
2. All code must have type hints and docstrings.
3. Respond ONLY with valid Python code.
4. NO markdown, NO backticks, NO code blocks.
5. First character must be 'd' (from 'def'), last must be ')' or '"'.
"""

config = types.GenerateContentConfig(
    temperature=0.0,
    top_p=0.1,
    top_k=1,
    max_output_tokens=8192,
    system_instruction=system_instruction,
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
    ],
)

prompt = "Write a Python function that receives a string and applies ROT13. Type hints. Docstring. Only code, no markdown."

print(f"=== CALLING {MODEL_NAME} via google-genai ===")
response = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=config)

raw_text = response.text
print("\n=== RAW RESPONSE ===")
print(raw_text)

print("\n=== CLEANED (no markdown) ===")
clean = re.sub(r'```python\n?', '', raw_text)
clean = re.sub(r'```\n?', '', clean)
clean = clean.strip()
print(clean)

print(f"\n=== TOKENS ===")
print(f"Input: {response.usage_metadata.prompt_token_count}")
print(f"Output: {response.usage_metadata.candidates_token_count}")
print(f"Total: {response.usage_metadata.total_token_count}")
