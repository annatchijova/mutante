# Copyright 2026 Anna Tchijova
#
# Licensed under the Apache License, Version 2.0

"""
windows_sandbox.py — EXPERIMENTAL. Not used in production.
Windows lacks POSIX rlimits; this module provides best-effort post-spawn limits.
"""

import os

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def apply_windows_sandbox_to_pid(pid: int) -> dict:
    """
    Best-effort Windows limit enforcement applied post-spawn.
    Must be called immediately after the MCP client spawns the process.
    """
    try:
        import resource
        return dict(success=False, error="NOT_WINDOWS: OS is POSIX, use preexec_fn instead.")
    except ImportError:
        pass  # We're actually on Windows

    if not _HAS_PSUTIL:
        return dict(success=False, error="MISSING_DEPENDENCY: psutil required for Windows sandbox.")

    try:
        p = psutil.Process(pid)
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        return dict(success=True, error=None)
    except Exception as e:
        return dict(success=False, error=f"PSUTIL_ERROR: {str(e)}")
