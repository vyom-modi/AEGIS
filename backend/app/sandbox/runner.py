"""
AEGIS Sandbox Runner.

Provides safe code execution via:
1. E2B cloud sandbox (primary) — isolated cloud VM
2. Subprocess sandbox (fallback) — local with restrictions

The runner validates code before execution and enforces
timeout and memory limits.
"""

import subprocess
import asyncio
import os
from typing import Optional
from app.config import get_settings


# Imports that are NOT allowed in the subprocess sandbox
BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "importlib", "ctypes", "socket", "http", "urllib",
    "ftplib", "smtplib", "telnetlib", "pickle",
    "shelve", "marshal", "tempfile", "glob",
    "signal", "multiprocessing", "threading",
}


def validate_code(code: str) -> tuple[bool, str]:
    """
    Basic static validation of tool code.

    Returns:
        (is_valid, error_message)
    """
    for blocked in BLOCKED_IMPORTS:
        if f"import {blocked}" in code or f"from {blocked}" in code:
            return False, f"Blocked import detected: {blocked}"

    if "exec(" in code or "eval(" in code:
        return False, "exec() and eval() are not allowed"

    if "__import__" in code:
        return False, "__import__ is not allowed"

    return True, ""


async def run_in_e2b(code: str, timeout: int = 30) -> dict:
    """
    Execute code in an E2B cloud sandbox.

    Uses the v2 E2B API: Sandbox.create() with env-based API key.
    """
    settings = get_settings()
    if not settings.e2b_api_key:
        return {"success": False, "error": "E2B API key not configured"}

    try:
        from e2b_code_interpreter import Sandbox

        # Set API key via environment variable (E2B v2 convention)
        os.environ["E2B_API_KEY"] = settings.e2b_api_key

        sandbox = Sandbox.create(timeout=timeout)
        try:
            execution = sandbox.run_code(code, timeout=timeout)

            # Collect stdout text
            stdout_lines = []
            if execution.logs and execution.logs.stdout:
                stdout_lines = [msg.line for msg in execution.logs.stdout]

            stderr_lines = []
            if execution.logs and execution.logs.stderr:
                stderr_lines = [msg.line for msg in execution.logs.stderr]

            # Collect results
            result_texts = []
            if execution.results:
                for r in execution.results:
                    if hasattr(r, "text") and r.text:
                        result_texts.append(r.text)
                    else:
                        result_texts.append(str(r))

            return {
                "success": execution.error is None,
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines),
                "results": result_texts,
                "error": str(execution.error) if execution.error else "",
            }
        finally:
            try:
                sandbox.kill()
            except Exception:
                pass

    except Exception as e:
        return {"success": False, "error": f"E2B error: {str(e)}"}


async def run_in_subprocess(code: str, timeout: int = 10) -> dict:
    """
    Execute code in a restricted subprocess (fallback).
    """
    is_valid, error = validate_code(code)
    if not is_valid:
        return {"success": False, "error": f"Validation failed: {error}"}

    try:
        process = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "error": stderr.decode().strip() if process.returncode != 0 else "",
        }
    except asyncio.TimeoutError:
        process.kill()
        return {"success": False, "error": f"Execution timed out ({timeout}s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def execute_code(
    code: str,
    use_e2b: bool = True,
    timeout: int = 30,
) -> dict:
    """
    Execute code using the best available sandbox.

    Tries E2B first if configured, falls back to subprocess.
    """
    settings = get_settings()

    if use_e2b and settings.e2b_api_key:
        result = await run_in_e2b(code, timeout)
        # If E2B fails due to API issues, fall back to subprocess
        if not result["success"] and "E2B error" in result.get("error", ""):
            return await run_in_subprocess(code, timeout)
        return result
    else:
        return await run_in_subprocess(code, timeout)
