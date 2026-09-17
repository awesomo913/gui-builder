"""Project management: save, load, export, and version GUI projects."""

import json
import logging
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .platform_utils import get_data_dir

logger = logging.getLogger(__name__)


@dataclass
class ProjectFile:
    """A single file in a project."""
    filename: str
    content: str
    language: str = "python"
    is_main: bool = False
    last_modified: float = field(default_factory=time.time)


@dataclass
class ProjectSnapshot:
    """A version snapshot of the project."""
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    files: dict[str, str] = field(default_factory=dict)


@dataclass
class Project:
    """A GUI Builder project."""
    name: str = "Untitled Project"
    description: str = ""
    framework: str = "customtkinter"
    style: str = "modern"
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    files: dict[str, ProjectFile] = field(default_factory=dict)
    conversation_history: list[dict] = field(default_factory=list)
    snapshots: list[ProjectSnapshot] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @property
    def main_file(self) -> Optional[ProjectFile]:
        """Get the main/entry-point file."""
        for f in self.files.values():
            if f.is_main:
                return f
        if self.files:
            return next(iter(self.files.values()))
        return None

    @property
    def main_code(self) -> str:
        """Get the main file's code content."""
        mf = self.main_file
        return mf.content if mf else ""

    def set_main_code(self, code: str, filename: str = "main.py") -> None:
        """Set or update the main file code."""
        if filename in self.files:
            self.files[filename].content = code
            self.files[filename].last_modified = time.time()
        else:
            self.files[filename] = ProjectFile(
                filename=filename,
                content=code,
                is_main=True,
            )
        self.modified = time.time()

    def add_file(self, filename: str, content: str, language: str = "python") -> None:
        """Add or update a file in the project."""
        self.files[filename] = ProjectFile(
            filename=filename,
            content=content,
            language=language,
            is_main=not self.files,
        )
        self.modified = time.time()

    def remove_file(self, filename: str) -> bool:
        """Remove a file from the project."""
        if filename in self.files:
            del self.files[filename]
            self.modified = time.time()
            return True
        return False

    def create_snapshot(self, description: str = "") -> ProjectSnapshot:
        """Create a version snapshot of the current state."""
        snap = ProjectSnapshot(
            description=description or f"Snapshot at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            files={name: f.content for name, f in self.files.items()},
        )
        self.snapshots.append(snap)
        if len(self.snapshots) > 50:
            self.snapshots = self.snapshots[-50:]
        return snap

    def restore_snapshot(self, index: int) -> bool:
        """Restore project files from a snapshot."""
        if 0 <= index < len(self.snapshots):
            snap = self.snapshots[index]
            self.create_snapshot("Auto-save before restore")
            for name, content in snap.files.items():
                if name in self.files:
                    self.files[name].content = content
                    self.files[name].last_modified = time.time()
                else:
                    self.add_file(name, content)
            self.modified = time.time()
            return True
        return False

    def to_dict(self) -> dict:
        """Serialize project to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "framework": self.framework,
            "style": self.style,
            "created": self.created,
            "modified": self.modified,
            "tags": self.tags,
            "metadata": self.metadata,
            "files": {
                name: {
                    "filename": f.filename,
                    "content": f.content,
                    "language": f.language,
                    "is_main": f.is_main,
                    "last_modified": f.last_modified,
                }
                for name, f in self.files.items()
            },
            "conversation_history": self.conversation_history,
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "description": s.description,
                    "files": s.files,
                }
                for s in self.snapshots[-10:]
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Deserialize project from dictionary."""
        proj = cls(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            framework=data.get("framework", "customtkinter"),
            style=data.get("style", "modern"),
            created=data.get("created", time.time()),
            modified=data.get("modified", time.time()),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            conversation_history=data.get("conversation_history", []),
        )
        for name, fdata in data.get("files", {}).items():
            proj.files[name] = ProjectFile(
                filename=fdata.get("filename", name),
                content=fdata.get("content", ""),
                language=fdata.get("language", "python"),
                is_main=fdata.get("is_main", False),
                last_modified=fdata.get("last_modified", time.time()),
            )
        for sdata in data.get("snapshots", []):
            proj.snapshots.append(ProjectSnapshot(
                timestamp=sdata.get("timestamp", time.time()),
                description=sdata.get("description", ""),
                files=sdata.get("files", {}),
            ))
        return proj


class ProjectManager:
    """Manage project persistence and operations."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._dir = data_dir or get_data_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._current: Optional[Project] = None
        self._autosave_path: Optional[Path] = None

    @property
    def current(self) -> Optional[Project]:
        return self._current

    @property
    def projects_dir(self) -> Path:
        return self._dir

    def new_project(
        self,
        name: str = "Untitled Project",
        framework: str = "customtkinter",
        style: str = "modern",
    ) -> Project:
        """Create a new empty project."""
        self._current = Project(
            name=name,
            framework=framework,
            style=style,
        )
        logger.info("New project created: %s", name)
        return self._current

    def save_project(self, project: Optional[Project] = None, path: Optional[Path] = None) -> Path:
        """Save project to disk as JSON."""
        proj = project or self._current
        if not proj:
            raise ValueError("No project to save")

        if path is None:
            safe_name = "".join(
                c if c.isalnum() or c in "._- " else "_"
                for c in proj.name
            ).strip()
            path = self._dir / f"{safe_name}.guiproject"

        proj.modified = time.time()
        data = proj.to_dict()
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Project saved: %s", path)
        return path

    def load_project(self, path: Path) -> Project:
        """Load a project from disk."""
        if not path.exists():
            raise FileNotFoundError(f"Project not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        self._current = Project.from_dict(data)
        logger.info("Project loaded: %s", self._current.name)
        return self._current

    def list_projects(self) -> list[dict]:
        """List all saved projects with summary info."""
        projects: list[dict] = []
        for p in sorted(self._dir.glob("*.guiproject"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                projects.append({
                    "name": data.get("name", p.stem),
                    "framework": data.get("framework", "unknown"),
                    "modified": data.get("modified", 0),
                    "file_count": len(data.get("files", {})),
                    "path": str(p),
                    "tags": data.get("tags", []),
                })
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping corrupt project %s: %s", p, exc)
        return projects

    def delete_project(self, path: Path) -> bool:
        """Delete a project file."""
        if path.exists() and path.suffix == ".guiproject":
            path.unlink()
            logger.info("Project deleted: %s", path)
            return True
        return False

    def duplicate_project(self, source_path: Path, new_name: str) -> Path:
        """Duplicate an existing project with a new name."""
        proj = self.load_project(source_path)
        proj.name = new_name
        proj.created = time.time()
        proj.modified = time.time()
        proj.snapshots.clear()
        return self.save_project(proj)

    def export_to_directory(
        self,
        output_dir: Path,
        project: Optional[Project] = None,
        include_requirements: bool = True,
    ) -> Path:
        """Export project files to a directory."""
        proj = project or self._current
        if not proj:
            raise ValueError("No project to export")

        output_dir.mkdir(parents=True, exist_ok=True)
        exported_files: list[str] = []

        for name, pfile in proj.files.items():
            file_path = output_dir / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(pfile.content, encoding="utf-8")
            exported_files.append(name)

        if include_requirements and proj.main_code:
            from .code_extractor import get_required_packages
            packages = get_required_packages(proj.main_code)
            if packages:
                req_path = output_dir / "requirements.txt"
                req_path.write_text("\n".join(packages) + "\n", encoding="utf-8")
                exported_files.append("requirements.txt")

        logger.info("Exported %d files to %s", len(exported_files), output_dir)
        return output_dir

    def export_single_file(
        self,
        output_path: Path,
        project: Optional[Project] = None,
    ) -> Path:
        """Export the main file to a specific path."""
        proj = project or self._current
        if not proj or not proj.main_code:
            raise ValueError("No code to export")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(proj.main_code, encoding="utf-8")
        logger.info("Exported main file to %s", output_path)
        return output_path

    def autosave(self, project: Optional[Project] = None) -> Optional[Path]:
        """Auto-save the current project."""
        proj = project or self._current
        if not proj:
            return None
        autosave_dir = self._dir / ".autosave"
        autosave_dir.mkdir(parents=True, exist_ok=True)
        path = autosave_dir / f"{proj.name}_autosave.guiproject"
        try:
            data = proj.to_dict()
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return path
        except OSError as exc:
            logger.error("Autosave failed: %s", exc)
            return None

    def recover_autosave(self) -> list[dict]:
        """List available autosave files for recovery."""
        autosave_dir = self._dir / ".autosave"
        if not autosave_dir.exists():
            return []
        results: list[dict] = []
        for p in autosave_dir.glob("*_autosave.guiproject"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                results.append({
                    "name": data.get("name", p.stem),
                    "modified": data.get("modified", 0),
                    "path": str(p),
                })
            except (json.JSONDecodeError, OSError):
                pass
        return results

    def import_from_file(self, source_path: Path, project_name: str = "") -> Project:
        """Import a standalone Python file as a new project."""
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {source_path}")
        code = source_path.read_text(encoding="utf-8")
        name = project_name or source_path.stem
        proj = self.new_project(name=name)
        proj.add_file(source_path.name, code, language="python")
        return proj
