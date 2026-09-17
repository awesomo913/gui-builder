"""Configuration management with auto-save and validation."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .platform_utils import get_config_dir

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DEFAULT_MODEL = "gemini-2.5-flash-preview-04-17"
AVAILABLE_MODELS = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

SUPPORTED_FRAMEWORKS = [
    "customtkinter",
    "tkinter",
    "pyqt6",
    "pyside6",
    "wxpython",
    "kivy",
    "dearpygui",
    "flet",
    "nicegui",
    "streamlit",
    "gradio",
    "html_css_js",
]

FRAMEWORK_DISPLAY = {
    "customtkinter": "CustomTkinter (Modern Desktop)",
    "tkinter": "Tkinter + ttk (Classic Desktop)",
    "pyqt6": "PyQt6 (Professional Desktop)",
    "pyside6": "PySide6 (Qt Desktop)",
    "wxpython": "wxPython (Native Desktop)",
    "kivy": "Kivy (Touch/Mobile)",
    "dearpygui": "Dear PyGui (GPU Accelerated)",
    "flet": "Flet (Flutter-based)",
    "nicegui": "NiceGUI (Web-based)",
    "streamlit": "Streamlit (Data Apps)",
    "gradio": "Gradio (ML Demos)",
    "html_css_js": "HTML/CSS/JS (Web)",
}


@dataclass
class AppConfig:
    """Application configuration with defaults."""
    api_key: str = ""
    model_name: str = DEFAULT_MODEL
    default_framework: str = "customtkinter"
    theme: str = "dark"
    font_size: int = 13
    max_tokens: int = 65536
    temperature: float = 0.7
    auto_save_interval_seconds: int = 300
    log_level: str = "INFO"
    window_width: int = 1400
    window_height: int = 900
    output_directory: str = ""
    include_docstrings: bool = True
    include_type_hints: bool = True
    include_error_handling: bool = True
    generate_requirements: bool = True
    auto_preview: bool = True
    preview_timeout_ms: int = 30000
    max_history_items: int = 50
    recent_projects: list = field(default_factory=list)
    favorite_components: list = field(default_factory=list)
    custom_prompts: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate configuration, return list of issues."""
        issues: list[str] = []
        if self.font_size < 8 or self.font_size > 32:
            issues.append(f"Font size {self.font_size} out of range [8, 32]")
            self.font_size = max(8, min(32, self.font_size))
        if self.temperature < 0.0 or self.temperature > 2.0:
            issues.append(f"Temperature {self.temperature} out of range [0.0, 2.0]")
            self.temperature = max(0.0, min(2.0, self.temperature))
        if self.max_tokens < 256 or self.max_tokens > 1048576:
            issues.append(f"Max tokens {self.max_tokens} out of range")
            self.max_tokens = max(256, min(1048576, self.max_tokens))
        if self.default_framework not in SUPPORTED_FRAMEWORKS:
            issues.append(f"Unknown framework: {self.default_framework}")
            self.default_framework = "customtkinter"
        if self.preview_timeout_ms < 5000 or self.preview_timeout_ms > 120000:
            self.preview_timeout_ms = max(5000, min(120000, self.preview_timeout_ms))
        return issues


class ConfigManager:
    """Load, save, and manage application configuration."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._dir = config_dir or get_config_dir()
        self._path = self._dir / CONFIG_FILE
        self.config = AppConfig()
        self.load()

    def load(self) -> AppConfig:
        """Load configuration from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for key, value in data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                issues = self.config.validate()
                for issue in issues:
                    logger.warning("Config validation: %s", issue)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load config: %s", exc)
        return self.config

    def save(self) -> bool:
        """Save configuration to disk."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            data = asdict(self.config)
            data.pop("api_key", None)
            self._path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except OSError as exc:
            logger.error("Failed to save config: %s", exc)
            return False

    def save_api_key(self, key: str) -> bool:
        """Save API key to a separate secured file."""
        self.config.api_key = key
        key_path = self._dir / ".api_key"
        try:
            key_path.write_text(key, encoding="utf-8")
            if hasattr(key_path, "chmod"):
                try:
                    key_path.chmod(0o600)
                except OSError:
                    pass
            return True
        except OSError as exc:
            logger.error("Failed to save API key: %s", exc)
            return False

    def load_api_key(self) -> str:
        """Load API key from the secured file."""
        key_path = self._dir / ".api_key"
        if key_path.exists():
            try:
                key = key_path.read_text(encoding="utf-8").strip()
                self.config.api_key = key
                return key
            except OSError:
                pass
        import os
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key:
            self.config.api_key = env_key
        return self.config.api_key

    def update(self, **kwargs: Any) -> list[str]:
        """Update config fields and validate."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        issues = self.config.validate()
        self.save()
        return issues

    def add_recent_project(self, project_path: str) -> None:
        """Add a project to the recent list (max 20)."""
        recents = self.config.recent_projects
        if project_path in recents:
            recents.remove(project_path)
        recents.insert(0, project_path)
        self.config.recent_projects = recents[:20]
        self.save()
