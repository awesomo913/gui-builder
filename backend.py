"""Backend orchestrator — single entry point for all backend operations."""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .config import ConfigManager, AppConfig, SUPPORTED_FRAMEWORKS
from .gemini_client import GUIGeminiClient, Conversation
from .code_extractor import (
    extract_code, extract_multiple_files, inject_main_guard,
    get_required_packages, ExtractedCode, MultiFileExtraction,
)
from .template_library import (
    get_all_templates, get_template_by_id, search_templates,
    get_templates_by_category, get_categories, Template,
)
from .project_manager import ProjectManager, Project
from .preview_runner import PreviewRunner, PreviewResult, validate_code_safety
from .prompt_engine import (
    get_component_list, get_style_list, get_framework_list,
    build_layout_prompt, build_clone_prompt, build_multifile_prompt,
)
from .logger_setup import setup_logging
from .diagnostics import generate_diagnostic_report, copy_report_to_clipboard

logger = logging.getLogger(__name__)


class GUIBuilderBackend:
    """Central backend coordinating all GUI Builder operations.

    This is the single object the UI layer interacts with.
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_mgr = ConfigManager(config_dir)
        self._config = self._config_mgr.config

        setup_logging(self._config.log_level)

        self._client = GUIGeminiClient(
            model_name=self._config.model_name,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
        )

        api_key = self._config_mgr.load_api_key()
        if api_key:
            self._client.configure(api_key)

        self._project_mgr = ProjectManager()
        self._preview = PreviewRunner(
            timeout_ms=self._config.preview_timeout_ms,
        )

        self._conversation: Optional[Conversation] = None
        self._autosave_timer: Optional[threading.Timer] = None
        self._generation_count = 0
        self._start_time = time.time()

        self._start_autosave()
        logger.info("GUI Builder backend initialized")

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def client(self) -> GUIGeminiClient:
        return self._client

    @property
    def project_manager(self) -> ProjectManager:
        return self._project_mgr

    @property
    def preview_runner(self) -> PreviewRunner:
        return self._preview

    @property
    def is_connected(self) -> bool:
        return self._client.is_configured

    @property
    def current_project(self) -> Optional[Project]:
        return self._project_mgr.current

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def set_api_key(self, key: str) -> tuple[bool, str]:
        """Set and validate the Gemini API key."""
        if not key.strip():
            return False, "API key cannot be empty"
        ok = self._client.configure(key.strip())
        if ok:
            self._config_mgr.save_api_key(key.strip())
            return True, "API key configured successfully"
        return False, "Failed to configure API key"

    def test_connection(self) -> tuple[bool, str]:
        """Test the Gemini API connection."""
        return self._client.test_connection()

    def update_settings(self, **kwargs: Any) -> list[str]:
        """Update application settings."""
        issues = self._config_mgr.update(**kwargs)
        if "model_name" in kwargs:
            self._client.update_settings(model_name=kwargs["model_name"])
        if "max_tokens" in kwargs:
            self._client.update_settings(max_tokens=kwargs["max_tokens"])
        if "temperature" in kwargs:
            self._client.update_settings(temperature=kwargs["temperature"])
        if "preview_timeout_ms" in kwargs:
            self._preview = PreviewRunner(timeout_ms=kwargs["preview_timeout_ms"])
        return issues

    def generate_gui(
        self,
        description: str,
        framework: Optional[str] = None,
        style: str = "modern",
        components: Optional[list[str]] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Generate a GUI from a description. Runs in a background thread."""
        fw = framework or self._config.default_framework

        if not self._conversation or self._conversation.framework != fw:
            self._conversation = Conversation(
                title=description[:50],
                framework=fw,
            )

        def _worker() -> None:
            try:
                raw = self._client.generate_gui(
                    description=description,
                    framework=fw,
                    style=style,
                    components=components,
                    conversation=self._conversation,
                    on_progress=on_progress,
                )
                extracted = extract_code(raw)
                self._generation_count += 1

                if self._project_mgr.current:
                    proj = self._project_mgr.current
                    proj.create_snapshot(f"Before generation #{self._generation_count}")
                    proj.set_main_code(extracted.code, extracted.filename)
                else:
                    proj = self._project_mgr.new_project(
                        name=description[:40],
                        framework=fw,
                        style=style,
                    )
                    proj.set_main_code(extracted.code, extracted.filename)

                if on_complete:
                    on_complete(extracted)

            except InterruptedError:
                if on_error:
                    on_error("Generation cancelled")
            except Exception as exc:
                logger.error("Generation failed: %s", exc)
                if on_error:
                    on_error(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def refine_gui(
        self,
        feedback: str,
        current_code: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Refine existing GUI code based on feedback. Background thread."""
        code = current_code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        if not code:
            if on_error:
                on_error("No code to refine. Generate a GUI first.")
            return

        fw = self._conversation.framework if self._conversation else self._config.default_framework

        def _worker() -> None:
            try:
                raw = self._client.refine_gui(
                    feedback=feedback,
                    current_code=code,
                    framework=fw,
                    conversation=self._conversation,
                    on_progress=on_progress,
                )
                extracted = extract_code(raw)

                if self._project_mgr.current:
                    proj = self._project_mgr.current
                    proj.create_snapshot(f"Before refinement: {feedback[:30]}")
                    proj.set_main_code(extracted.code, extracted.filename)

                if on_complete:
                    on_complete(extracted)
            except InterruptedError:
                if on_error:
                    on_error("Refinement cancelled")
            except Exception as exc:
                logger.error("Refinement failed: %s", exc)
                if on_error:
                    on_error(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def add_component(
        self,
        component_type: str,
        placement: str = "",
        current_code: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Add a component to existing code. Background thread."""
        code = current_code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        if not code:
            if on_error:
                on_error("No code to add component to. Generate a GUI first.")
            return

        fw = self._conversation.framework if self._conversation else self._config.default_framework

        def _worker() -> None:
            try:
                raw = self._client.add_component(
                    component_type=component_type,
                    current_code=code,
                    placement=placement,
                    framework=fw,
                    conversation=self._conversation,
                    on_progress=on_progress,
                )
                extracted = extract_code(raw)

                if self._project_mgr.current:
                    proj = self._project_mgr.current
                    proj.create_snapshot(f"Before adding {component_type}")
                    proj.set_main_code(extracted.code, extracted.filename)

                if on_complete:
                    on_complete(extracted)
            except Exception as exc:
                logger.error("Add component failed: %s", exc)
                if on_error:
                    on_error(str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def generate_from_template(
        self,
        template_id: str,
        framework: Optional[str] = None,
        style: str = "modern",
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Generate code from a built-in template."""
        template = get_template_by_id(template_id)
        if not template:
            if on_error:
                on_error(f"Template not found: {template_id}")
            return

        fw = framework or self._config.default_framework
        self.generate_gui(
            description=template.prompt,
            framework=fw,
            style=style,
            components=template.components,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

    def generate_layout(
        self,
        layout_type: str,
        panel_count: int = 2,
        framework: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Generate a layout skeleton."""
        fw = framework or self._config.default_framework
        prompt = build_layout_prompt(layout_type, panel_count, fw)
        self.generate_gui(
            description=prompt,
            framework=fw,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

    def generate_clone(
        self,
        target_app: str,
        framework: Optional[str] = None,
        style: str = "modern",
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExtractedCode], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Generate a GUI that mimics a known app's layout."""
        fw = framework or self._config.default_framework
        prompt = build_clone_prompt(target_app, fw, style)
        self.generate_gui(
            description=prompt,
            framework=fw,
            style=style,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

    def cancel_generation(self) -> None:
        """Cancel the current generation."""
        self._client.cancel()

    def preview_code(
        self,
        code: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[PreviewResult], None]] = None,
    ) -> None:
        """Preview the current or provided code."""
        code = code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        if not code:
            if on_error:
                on_error("No code to preview")
            return
        self._preview.run_preview(
            code=code,
            on_output=on_output,
            on_error=on_error,
            on_complete=on_complete,
        )

    def stop_preview(self) -> bool:
        """Stop the running preview."""
        return self._preview.stop_preview()

    def check_code(self, code: Optional[str] = None) -> PreviewResult:
        """Quick syntax/import check."""
        code = code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        if not code:
            return PreviewResult(error="No code to check")
        return self._preview.run_check(code)

    def validate_safety(self, code: Optional[str] = None) -> tuple[bool, list[str]]:
        """Validate code safety."""
        code = code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        if not code:
            return True, []
        return validate_code_safety(code)

    def new_project(self, name: str = "Untitled", framework: Optional[str] = None, style: str = "modern") -> Project:
        """Create a new empty project."""
        fw = framework or self._config.default_framework
        self._conversation = None
        return self._project_mgr.new_project(name, fw, style)

    def save_project(self, path: Optional[Path] = None) -> Optional[Path]:
        """Save the current project."""
        try:
            return self._project_mgr.save_project(path=path)
        except Exception as exc:
            logger.error("Save failed: %s", exc)
            return None

    def load_project(self, path: Path) -> Optional[Project]:
        """Load a project from disk."""
        try:
            proj = self._project_mgr.load_project(path)
            self._conversation = None
            self._config_mgr.add_recent_project(str(path))
            return proj
        except Exception as exc:
            logger.error("Load failed: %s", exc)
            return None

    def export_project(self, output_dir: Path) -> Optional[Path]:
        """Export project files to a directory."""
        try:
            return self._project_mgr.export_to_directory(output_dir)
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            return None

    def export_single(self, output_path: Path) -> Optional[Path]:
        """Export the main file."""
        try:
            return self._project_mgr.export_single_file(output_path)
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            return None

    def list_projects(self) -> list[dict]:
        """List all saved projects."""
        return self._project_mgr.list_projects()

    def undo(self) -> bool:
        """Undo to the previous snapshot."""
        proj = self._project_mgr.current
        if proj and proj.snapshots:
            return proj.restore_snapshot(len(proj.snapshots) - 1)
        return False

    def get_templates(self, category: Optional[str] = None, search: Optional[str] = None) -> list[Template]:
        """Get available templates."""
        if search:
            return search_templates(search)
        if category:
            return get_templates_by_category(category)
        return get_all_templates()

    def get_template_categories(self) -> dict[str, str]:
        return get_categories()

    def get_components(self) -> dict[str, str]:
        return get_component_list()

    def get_styles(self) -> dict[str, str]:
        return get_style_list()

    def get_frameworks(self) -> dict[str, str]:
        return get_framework_list()

    def get_required_packages(self, code: Optional[str] = None) -> list[str]:
        """Get pip packages required for the code."""
        code = code or (self._project_mgr.current.main_code if self._project_mgr.current else "")
        return get_required_packages(code) if code else []

    def run_diagnostics(self) -> tuple[str, Optional[Path]]:
        """Generate and save a diagnostic report."""
        return generate_diagnostic_report(config=self._config)

    def copy_diagnostics(self, report: str) -> bool:
        """Copy diagnostic report to clipboard."""
        return copy_report_to_clipboard(report)

    def new_conversation(self, framework: Optional[str] = None) -> Conversation:
        """Start a fresh conversation."""
        fw = framework or self._config.default_framework
        self._conversation = Conversation(framework=fw)
        return self._conversation

    def get_conversation(self) -> Optional[Conversation]:
        return self._conversation

    def get_stats(self) -> dict[str, Any]:
        """Get backend statistics."""
        return {
            "uptime_seconds": self.uptime_seconds,
            "generation_count": self._generation_count,
            "is_connected": self.is_connected,
            "model": self._client.model_name,
            "framework": self._config.default_framework,
            "project_name": self._project_mgr.current.name if self._project_mgr.current else None,
            "preview_running": self._preview.is_running,
        }

    def _start_autosave(self) -> None:
        """Start the autosave timer."""
        interval = self._config.auto_save_interval_seconds
        if interval <= 0:
            return

        def _tick() -> None:
            self._project_mgr.autosave()
            self._autosave_timer = threading.Timer(interval, _tick)
            self._autosave_timer.daemon = True
            self._autosave_timer.start()

        self._autosave_timer = threading.Timer(interval, _tick)
        self._autosave_timer.daemon = True
        self._autosave_timer.start()

    def shutdown(self) -> None:
        """Clean shutdown of all backend resources."""
        logger.info("Shutting down GUI Builder backend")
        if self._autosave_timer:
            self._autosave_timer.cancel()
        self._project_mgr.autosave()
        self._preview.cleanup()
        self._config_mgr.save()
        logger.info("Backend shutdown complete")
