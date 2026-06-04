#!/usr/bin/env python3
# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""
sandbox.py — Secure Execution Environment Limits for MUTANTE.
PLATFORM: Linux only (POSIX). Verified on Linux Mint / Debian.
"""

import os
import sys
import asyncio
import unicodedata
import resource

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

# Configuration via environment variables
MUTANTE_LLM_TIMEOUT = float(os.getenv("MUTANTE_LLM_TIMEOUT", "30.0"))
MUTANTE_MAX_RESPONSE_CHARS = int(os.getenv("MUTANTE_MAX_RESPONSE_CHARS", "8000"))
MUTANTE_MAX_PROMPT_BYTES = int(os.getenv("MUTANTE_MAX_PROMPT_BYTES", "32768"))
MUTANTE_MAX_OUTPUT_BYTES = int(os.getenv("MUTANTE_MAX_OUTPUT_BYTES", str(512 * 1024)))


def sanitize_mutation_input(prompt: str, max_bytes: int | None = None) -> dict:
    """
    Sanitizes attacker-controlled strings before processing.
    
    Applies NFC normalization and strips NUL bytes, ZWNJ, ZWJ, ZWSP, and BOM.
    Enforces strict byte-length limit to prevent buffer saturation.
    
    Args:
        prompt: Raw attacker-controlled string.
        max_bytes: Maximum allowed bytes. Defaults to MUTANTE_MAX_PROMPT_BYTES.
    
    Returns:
        dict with 'text', 'rejected' bool, and 'reason'.
    """
    limit = max_bytes if max_bytes is not None else MUTANTE_MAX_PROMPT_BYTES
    
    prompt_bytes = prompt.encode("utf-8", errors="ignore")
    if len(prompt_bytes) > limit:
        return dict(
            text="",
            rejected=True,
            reason=f"PROMPT_TOO_LARGE: {len(prompt_bytes)} bytes exceeds {limit} byte limit."
        )
    
    # Strip dangerous Unicode control characters
    clean_text = (
        prompt
        .replace("\x00", "")      # NUL
        .replace("\u200c", "")     # ZWNJ
        .replace("\u200d", "")     # ZWJ
        .replace("\u200b", "")     # ZWSP
        .replace("\ufeff", "")     # BOM
    )
    clean_text = unicodedata.normalize("NFC", clean_text)
    
    return dict(text=clean_text, rejected=False, reason=None)


async def sandboxed_llm_call(model, mutated_prompt: str, timeout_seconds: float | None = None) -> dict:
    """
    Wraps generative model calls with asyncio timeout and error handling.
    
    Args:
        model: The generative model instance.
        mutated_prompt: Sanitized adversarial prompt.
        timeout_seconds: Max time for API call.
    
    Returns:
        dict with 'text', 'truncated', 'error', 'token_count'.
    """
    timeout = timeout_seconds if timeout_seconds is not None else MUTANTE_LLM_TIMEOUT
    
    sanitized = sanitize_mutation_input(mutated_prompt)
    if sanitized["rejected"]:
        return dict(text="", truncated=False, error=sanitized["reason"], token_count=None)
    
    safe_prompt = sanitized["text"]
    
    try:
        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, model.generate_content, safe_prompt)
        response = await asyncio.wait_for(task, timeout=timeout)
        
        response_text = ""
        error_msg = None
        
        try:
            if hasattr(response, "candidates") and (not response.candidates or len(response.candidates) == 0):
                error_msg = "SAFETY_BLOCK: Response candidates array is empty."
            else:
                response_text = response.text
        except ValueError as ve:
            error_msg = f"SAFETY_BLOCK_OR_EMPTY: {str(ve)}"
        
        truncated = False
        if response_text and len(response_text) > MUTANTE_MAX_RESPONSE_CHARS:
            response_text = response_text[:MUTANTE_MAX_RESPONSE_CHARS]
            truncated = True
        
        token_count = None
        usage = getattr(response, "usage_metadata", None)
        if usage:
            token_count = getattr(usage, "candidates_token_count", None)
        
        return dict(text=response_text, truncated=truncated, error=error_msg, token_count=token_count)
        
    except asyncio.TimeoutError:
        return dict(
            text="",
            truncated=False,
            error=f"LLM_TIMEOUT: Call exceeded {timeout} seconds.",
            token_count=None
        )
    except Exception as e:
        return dict(text="", truncated=False, error=f"LLM_ERROR: {str(e)}", token_count=None)


def _preexec_sandbox(max_memory_mb: int = 512, max_cpu_seconds: int = 60) -> callable:
    """
    Returns a preexec_fn for subprocess.Popen that applies POSIX rlimits.
    
    Args:
        max_memory_mb: Hard limit for virtual memory (RLIMIT_AS).
        max_cpu_seconds: Hard limit for CPU time (RLIMIT_CPU).
    
    Returns:
        Callable to pass as preexec_fn.
    """
    def preexec_fn():
        try:
            mem_bytes = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (MUTANTE_MAX_OUTPUT_BYTES, MUTANTE_MAX_OUTPUT_BYTES))
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        except Exception as e:
            try:
                os.write(2, f"FATAL_SETRLIMIT_ERROR: {str(e)}\n".encode("utf-8"))
            except Exception:
                pass
            os._exit(1)
    return preexec_fn


async def sandboxed_mcp_spawn(
    script_path: str,
    env: dict[str, str],
    max_memory_mb: int = 512,
    max_cpu_seconds: int = 60
) -> dict:
    """
    Prepares a safe subprocess configuration for MCP connections.
    
    Validates paths, sanitizes environment variables, and returns a dict
    compatible with StdioServerParameters.
    
    Args:
        script_path: Absolute path to the target Python script.
        env: Environment variables for the subprocess.
        max_memory_mb: Hard limit for virtual memory.
        max_cpu_seconds: Hard limit for CPU time.
    
    Returns:
        dict with 'command', 'args', 'env', 'preexec_fn' for POSIX systems.
    """
    resolved_path = os.path.realpath(script_path)

    if not os.path.isabs(resolved_path):
        return dict(error=f"INVALID_PATH: Path must be absolute, got {resolved_path}")
    
    if not resolved_path.endswith(".py"):
        return dict(error=f"INVALID_EXTENSION: Must end in .py, got {resolved_path}")
    
    if not os.path.exists(resolved_path):
        return dict(error=f"FILE_NOT_FOUND: {resolved_path}")

    safe_env = env.copy()
    for dangerous_key in ["LD_PRELOAD", "PYTHONINSPECT", "PYTHONPATH"]:
        safe_env.pop(dangerous_key, None)

    return dict(
        command=sys.executable,
        args=[resolved_path],
        env=safe_env,
        preexec_fn=_preexec_sandbox(max_memory_mb, max_cpu_seconds),
    )
