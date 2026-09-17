"""Platform detection and path utilities."""

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


APP_DIR_NAME = "gui_builder"


@dataclass
class PlatformInfo:
    """Detected platform information."""
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    machine: str = ""
    python_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    total_ram_mb: int = 0
    available_disk_gb: float = 0.0
    hostname: str = ""


def detect_platform() -> PlatformInfo:
    """Detect the current platform capabilities."""
    info = PlatformInfo(
        os_name=platform.system(),
        os_version=platform.version(),
        architecture=platform.architecture()[0],
        machine=platform.machine(),
        python_version=platform.python_version(),
        hostname=platform.node(),
    )
    try:
        import psutil
        info.total_ram_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        info.available_disk_gb = round(
            psutil.disk_usage(str(Path.home())).free / (1024 ** 3), 1
        )
    except ImportError:
        pass
    try:
        import tkinter as tk
        root = tk.Tk()
        info.screen_width = root.winfo_screenwidth()
        info.screen_height = root.winfo_screenheight()
        root.destroy()
    except Exception:
        pass
    return info


def get_desktop_path() -> Path:
    """Get the user's desktop path with fallback."""
    desktop = Path.home() / "Desktop"
    if desktop.exists() and desktop.is_dir():
        return desktop
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "[Environment]::GetFolderPath('Desktop')"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                p = Path(result.stdout.strip())
                if p.exists():
                    return p
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return Path.home()


def get_config_dir() -> Path:
    """Get the application configuration directory."""
    if platform.system() == "Windows":
        import os
        base = Path(os.environ.get(
            "APPDATA", str(Path.home() / "AppData" / "Roaming")
        ))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        import os
        base = Path(os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config")
        ))
    config_dir = base / APP_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the application data directory for projects."""
    data_dir = get_config_dir() / "projects"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_log_dir() -> Path:
    """Get the application log directory."""
    log_dir = get_config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_templates_dir() -> Path:
    """Get the built-in templates directory."""
    return Path(__file__).parent / "templates"
