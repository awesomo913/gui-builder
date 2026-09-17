"""Sandbox preview runner for generated GUI code."""

import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_POLL_INTERVAL_MS = 50


@dataclass
class PreviewResult:
    """Result of a preview execution."""
    stdout: str = ""
    stderr: str = ""
    return_code: Optional[int] = None
    timed_out: bool = False
    elapsed_ms: float = 0.0
    pid: Optional[int] = None
    temp_file: Optional[str] = None
    success: bool = False
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.success and not self.timed_out and self.error is None


_BLOCKED_IMPORTS = {
    "ctypes", "ctypes.wintypes",
    "winreg", "_winapi",
}

_BLOCKED_CALLS = [
    "os.system(",
    "subprocess.call(",
    "subprocess.Popen(",
    "subprocess.run(",
    "shutil.rmtree(",
    "os.remove(",
    "os.unlink(",
    "os.rmdir(",
    "__import__(",
    "importlib.import_module(",
]


def validate_code_safety(code: str) -> tuple[bool, list[str]]:
    """Check code for potentially dangerous operations before execution."""
    warnings: list[str] = []

    for blocked in _BLOCKED_CALLS:
        if blocked in code:
            warnings.append(f"Blocked call detected: {blocked.rstrip('(')}")

    import re
    for imp_match in re.finditer(r"(?:import|from)\s+(\S+)", code):
        module = imp_match.group(1).split(".")[0]
        if module in _BLOCKED_IMPORTS:
            warnings.append(f"Blocked import: {module}")

    if "eval(" in code:
        if "ast.literal_eval" not in code:
            warnings.append("eval() without ast.literal_eval — potential injection")

    if "exec(" in code:
        warnings.append("exec() call — potential injection")

    is_safe = len(warnings) == 0
    return is_safe, warnings


class PreviewRunner:
    """Run generated GUI code in a sandboxed subprocess."""

    def __init__(
        self,
        timeout_ms: int = 30000,
        python_path: Optional[str] = None,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._python = python_path or sys.executable
        self._process: Optional[subprocess.Popen] = None
        self._temp_dir = tempfile.mkdtemp(prefix="gui_builder_preview_")
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def run_preview(
        self,
        code: str,
        filename: str = "preview.py",
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[PreviewResult], None]] = None,
        blocking: bool = False,
        validate: bool = True,
    ) -> PreviewResult:
        """Run code in a preview subprocess."""
        if validate:
            is_safe, warnings = validate_code_safety(code)
            if not is_safe:
                result = PreviewResult(
                    stderr="\n".join(f"SAFETY: {w}" for w in warnings),
                    error="Code safety validation failed",
                    success=False,
                )
                if on_error:
                    on_error(result.stderr)
                if on_complete:
                    on_complete(result)
                return result

        temp_file = Path(self._temp_dir) / filename
        temp_file.write_text(code, encoding="utf-8")

        if blocking:
            return self._run_blocking(str(temp_file), on_output, on_error)

        thread = threading.Thread(
            target=self._run_async,
            args=(str(temp_file), on_output, on_error, on_complete),
            daemon=True,
        )
        thread.start()
        return PreviewResult(
            temp_file=str(temp_file),
            pid=None,
        )

    def _run_blocking(
        self,
        script_path: str,
        on_output: Optional[Callable[[str], None]],
        on_error: Optional[Callable[[str], None]],
    ) -> PreviewResult:
        """Run script and wait for completion or timeout."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        started = time.monotonic()
        try:
            with self._lock:
                self._process = subprocess.Popen(
                    [self._python, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    cwd=str(Path(script_path).parent),
                )
                self._running = True

            pid = self._process.pid
            deadline_s = self._timeout_ms / 1000.0

            while True:
                retcode = self._process.poll()
                if retcode is not None:
                    elapsed = (time.monotonic() - started) * 1000
                    stdout = self._process.stdout.read().decode("utf-8", errors="replace") if self._process.stdout else ""
                    stderr = self._process.stderr.read().decode("utf-8", errors="replace") if self._process.stderr else ""

                    if on_output and stdout:
                        on_output(stdout)
                    if on_error and stderr:
                        on_error(stderr)

                    self._running = False
                    return PreviewResult(
                        stdout=stdout,
                        stderr=stderr,
                        return_code=retcode,
                        elapsed_ms=elapsed,
                        pid=pid,
                        temp_file=script_path,
                        success=retcode == 0,
                    )

                if (time.monotonic() - started) >= deadline_s:
                    self._process.kill()
                    try:
                        self._process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass

                    self._running = False
                    msg = f"Preview timed out after {self._timeout_ms}ms"
                    if on_error:
                        on_error(msg)
                    return PreviewResult(
                        stderr=msg,
                        timed_out=True,
                        elapsed_ms=self._timeout_ms,
                        pid=pid,
                        temp_file=script_path,
                    )

                time.sleep(_POLL_INTERVAL_MS / 1000.0)

        except Exception as exc:
            self._running = False
            msg = f"Preview failed: {exc}"
            if on_error:
                on_error(msg)
            return PreviewResult(
                stderr=msg,
                error=str(exc),
                elapsed_ms=(time.monotonic() - started) * 1000,
                temp_file=script_path,
            )

    def _run_async(
        self,
        script_path: str,
        on_output: Optional[Callable[[str], None]],
        on_error: Optional[Callable[[str], None]],
        on_complete: Optional[Callable[[PreviewResult], None]],
    ) -> None:
        """Run script asynchronously in a thread."""
        result = self._run_blocking(script_path, on_output, on_error)
        if on_complete:
            on_complete(result)

    def stop_preview(self) -> bool:
        """Stop the currently running preview."""
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.kill()
                try:
                    self._process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                self._running = False
                logger.info("Preview stopped")
                return True
        return False

    def run_check(self, code: str) -> PreviewResult:
        """Quick syntax/import check without running the GUI."""
        check_code = f'''
import ast
import sys

code = {repr(code)}

try:
    tree = ast.parse(code)
    print("SYNTAX_OK")

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    failed = []
    for imp in imports:
        top = imp.split(".")[0]
        try:
            __import__(top)
        except ImportError:
            failed.append(top)

    if failed:
        print("MISSING_IMPORTS:" + ",".join(failed))
        sys.exit(1)
    else:
        print("IMPORTS_OK")
        sys.exit(0)

except SyntaxError as e:
    print(f"SYNTAX_ERROR:{{e.lineno}}:{{e.msg}}")
    sys.exit(1)
'''
        temp_file = Path(self._temp_dir) / "_check.py"
        temp_file.write_text(check_code, encoding="utf-8")

        try:
            result = subprocess.run(
                [self._python, str(temp_file)],
                capture_output=True,
                timeout=10,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            return PreviewResult(
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode,
                success=result.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            return PreviewResult(stderr="Check timed out", timed_out=True)
        except Exception as exc:
            return PreviewResult(stderr=str(exc), error=str(exc))

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.stop_preview()
        try:
            import shutil
            if Path(self._temp_dir).exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception as exc:
            logger.warning("Cleanup failed: %s", exc)

    def __del__(self) -> None:
        self.cleanup()
