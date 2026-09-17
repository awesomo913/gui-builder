"""Diagnostic report generation."""

import logging
import platform
import sys
import time
from pathlib import Path
from typing import Optional

from . import __version__, __app_name__
from .platform_utils import detect_platform, get_desktop_path, get_config_dir
from .logger_setup import get_recent_errors

logger = logging.getLogger(__name__)

REQUIRED_PACKAGES = [
    "google-genai",
    "customtkinter",
    "Pillow",
    "psutil",
]

OPTIONAL_PACKAGES = [
    "PyQt6",
    "PySide6",
    "wxPython",
    "kivy",
    "dearpygui",
    "flet",
    "nicegui",
    "streamlit",
    "gradio",
]


def generate_diagnostic_report(
    config: Optional[object] = None,
    save_to_desktop: bool = True,
    include_config: bool = True,
) -> tuple[str, Optional[Path]]:
    """Generate a comprehensive diagnostic report.

    Returns (report_text, saved_path_or_none).
    """
    sections: list[str] = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    sections.append("=" * 70)
    sections.append(f"  {__app_name__} v{__version__} — Diagnostic Report")
    sections.append(f"  Generated: {timestamp}")
    sections.append("=" * 70)
    sections.append("")
    sections.append("To share this report for support, copy-paste the full text")
    sections.append("or attach the file. No passwords or API keys are included.")
    sections.append("")

    info = detect_platform()
    sections.append("-" * 40)
    sections.append("SYSTEM INFORMATION")
    sections.append("-" * 40)
    sections.append(f"  OS:             {info.os_name} {info.os_version}")
    sections.append(f"  Architecture:   {info.architecture} ({info.machine})")
    sections.append(f"  Python:         {info.python_version}")
    sections.append(f"  Python Path:    {sys.executable}")
    sections.append(f"  Hostname:       {info.hostname}")
    sections.append(f"  Screen:         {info.screen_width}x{info.screen_height}")
    sections.append(f"  RAM:            {info.total_ram_mb} MB")
    sections.append(f"  Disk Free:      {info.available_disk_gb} GB")
    sections.append("")

    if include_config and config:
        sections.append("-" * 40)
        sections.append("APP CONFIGURATION")
        sections.append("-" * 40)
        safe_fields = [
            "model_name", "default_framework", "theme", "font_size",
            "max_tokens", "temperature", "auto_save_interval_seconds",
            "log_level", "window_width", "window_height",
            "include_docstrings", "include_type_hints",
            "auto_preview", "preview_timeout_ms",
        ]
        for field_name in safe_fields:
            value = getattr(config, field_name, None)
            if value is not None:
                sections.append(f"  {field_name}: {value}")
        has_key = bool(getattr(config, "api_key", ""))
        sections.append(f"  api_key_set: {has_key}")
        sections.append("")

    sections.append("-" * 40)
    sections.append("DEPENDENCY CHECK")
    sections.append("-" * 40)

    for pkg in REQUIRED_PACKAGES:
        status, version = _check_package(pkg)
        marker = "OK" if status else "MISSING"
        ver_str = f" ({version})" if version else ""
        sections.append(f"  [{marker:>7}] {pkg}{ver_str}")

    sections.append("")
    sections.append("  Optional framework packages:")
    for pkg in OPTIONAL_PACKAGES:
        status, version = _check_package(pkg)
        marker = "OK" if status else "—"
        ver_str = f" ({version})" if version else ""
        sections.append(f"  [{marker:>7}] {pkg}{ver_str}")
    sections.append("")

    sections.append("-" * 40)
    sections.append("PERFORMANCE")
    sections.append("-" * 40)
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        sections.append(f"  Process Memory:  {mem.rss / (1024*1024):.1f} MB RSS")
        sections.append(f"  CPU Percent:     {proc.cpu_percent(interval=0.5):.1f}%")
        sections.append(f"  Open Files:      {len(proc.open_files())}")
        sections.append(f"  Threads:         {proc.num_threads()}")
    except Exception as exc:
        sections.append(f"  (psutil unavailable: {exc})")
    sections.append("")

    sections.append("-" * 40)
    sections.append("CONNECTIVITY")
    sections.append("-" * 40)
    net_ok, net_msg = _check_network()
    sections.append(f"  Internet:        {'OK' if net_ok else 'FAILED'} — {net_msg}")

    gemini_ok = _check_gemini_reachable()
    sections.append(f"  Gemini API:      {'Reachable' if gemini_ok else 'Unreachable'}")
    sections.append("")

    sections.append("-" * 40)
    sections.append("RECENT ERRORS (last 50)")
    sections.append("-" * 40)
    errors = get_recent_errors(50)
    if errors:
        for err in errors:
            sections.append(f"  {err}")
    else:
        sections.append("  No recent errors found.")
    sections.append("")

    sections.append("-" * 40)
    sections.append("FILE SYSTEM")
    sections.append("-" * 40)
    config_dir = get_config_dir()
    sections.append(f"  Config Dir:      {config_dir}")
    sections.append(f"  Config Exists:   {config_dir.exists()}")
    projects_dir = config_dir / "projects"
    if projects_dir.exists():
        project_count = len(list(projects_dir.glob("*.guiproject")))
        sections.append(f"  Projects:        {project_count}")
    sections.append("")
    sections.append("=" * 70)
    sections.append("  END OF REPORT")
    sections.append("=" * 70)

    report = "\n".join(sections)

    saved_path = None
    if save_to_desktop:
        desktop = get_desktop_path()
        ts = time.strftime("%Y-%m-%d_%H%M%S")
        filename = f"gui_builder_diagnostic_{ts}.txt"
        saved_path = desktop / filename
        try:
            saved_path.write_text(report, encoding="utf-8")
            logger.info("Diagnostic report saved: %s", saved_path)
        except OSError as exc:
            logger.error("Failed to save diagnostic: %s", exc)
            saved_path = None

    return report, saved_path


def _check_package(name: str) -> tuple[bool, str]:
    """Check if a package is installed and get its version."""
    try:
        from importlib.metadata import version as get_version
        ver = get_version(name)
        return True, ver
    except Exception:
        return False, ""


def _check_network() -> tuple[bool, str]:
    """Check basic internet connectivity."""
    import urllib.request
    try:
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True, "Connected"
    except Exception as exc:
        return False, str(exc)


def _check_gemini_reachable() -> bool:
    """Check if Gemini API endpoint is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(
            "https://generativelanguage.googleapis.com/", timeout=5,
        )
        return True
    except Exception:
        return False


def copy_report_to_clipboard(report: str) -> bool:
    """Copy the diagnostic report to the system clipboard."""
    try:
        if platform.system() == "Windows":
            import subprocess
            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=False,
            )
            process.communicate(report.encode("utf-8"))
            return process.returncode == 0
        elif platform.system() == "Darwin":
            import subprocess
            process = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE,
            )
            process.communicate(report.encode("utf-8"))
            return process.returncode == 0
        else:
            import subprocess
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            process.communicate(report.encode("utf-8"))
            return process.returncode == 0
    except Exception as exc:
        logger.warning("Clipboard copy failed: %s", exc)
        return False
