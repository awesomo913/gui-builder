"""Extract and validate code from Gemini API responses."""

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedCode:
    """Result of code extraction from an API response."""
    code: str = ""
    language: str = "python"
    filename: str = "generated_gui.py"
    is_valid: bool = False
    syntax_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    has_main_guard: bool = False
    line_count: int = 0


@dataclass
class MultiFileExtraction:
    """Result of extracting multiple files from a response."""
    files: dict[str, ExtractedCode] = field(default_factory=dict)
    total_valid: int = 0
    total_invalid: int = 0


_CODE_FENCE_RE = re.compile(
    r"```(\w*)\s*\n(.*?)```",
    re.DOTALL,
)

_FILENAME_RE = re.compile(
    r"^#\s*(?:file(?:name)?:\s*)?(\S+\.(?:py|html|css|js|kv))\s*$",
    re.IGNORECASE,
)

_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(\S+)", re.MULTILINE)

_DANGEROUS_PATTERNS = [
    (r"\bos\.system\s*\(", "os.system() call detected — use subprocess instead"),
    (r"\beval\s*\(", "eval() call detected — potential code injection"),
    (r"\bexec\s*\(", "exec() call detected — potential code injection"),
    (r"\b__import__\s*\(", "__import__() call detected"),
    (r"\bsubprocess\.call\s*\(.*shell\s*=\s*True", "subprocess with shell=True"),
    (r"\bopen\s*\([^)]*['\"]w['\"]", "File write operation — verify intent"),
    (r"\bshutil\.rmtree\s*\(", "Recursive directory deletion"),
    (r"\bos\.remove\s*\(", "File deletion operation"),
]


def extract_code(response: str) -> ExtractedCode:
    """Extract the primary code block from a Gemini response."""
    matches = _CODE_FENCE_RE.findall(response)
    if not matches:
        stripped = response.strip()
        if stripped and _looks_like_code(stripped):
            return _analyze_code(stripped, "python", "generated_gui.py")
        return ExtractedCode(code=response, warnings=["No code fence found in response"])

    python_blocks = [
        (lang, code) for lang, code in matches
        if lang.lower() in ("python", "py", "")
    ]

    if python_blocks:
        lang, code = python_blocks[0]
        if len(python_blocks) > 1:
            longest = max(python_blocks, key=lambda x: len(x[1]))
            lang, code = longest
    else:
        lang, code = matches[0]

    code = code.strip()

    filename = "generated_gui.py"
    first_line = code.split("\n", 1)[0].strip()
    fname_match = _FILENAME_RE.match(first_line)
    if fname_match:
        filename = fname_match.group(1)
        code = code.split("\n", 1)[1].strip() if "\n" in code else ""

    detected_lang = lang.lower() if lang else "python"
    if detected_lang in ("py", ""):
        detected_lang = "python"

    return _analyze_code(code, detected_lang, filename)


def extract_multiple_files(response: str) -> MultiFileExtraction:
    """Extract multiple code files from a response."""
    result = MultiFileExtraction()
    matches = _CODE_FENCE_RE.findall(response)

    if not matches:
        single = extract_code(response)
        if single.code:
            result.files[single.filename] = single
            if single.is_valid:
                result.total_valid = 1
            else:
                result.total_invalid = 1
        return result

    file_counter: dict[str, int] = {}

    for lang, code in matches:
        code = code.strip()
        if not code:
            continue

        filename = "generated_gui.py"
        detected_lang = lang.lower() if lang else "python"

        first_line = code.split("\n", 1)[0].strip()
        fname_match = _FILENAME_RE.match(first_line)
        if fname_match:
            filename = fname_match.group(1)
            code = code.split("\n", 1)[1].strip() if "\n" in code else ""

        if filename in result.files:
            base, ext = filename.rsplit(".", 1) if "." in filename else (filename, "py")
            count = file_counter.get(base, 1) + 1
            file_counter[base] = count
            filename = f"{base}_{count}.{ext}"

        extracted = _analyze_code(code, detected_lang, filename)
        result.files[filename] = extracted
        if extracted.is_valid:
            result.total_valid += 1
        else:
            result.total_invalid += 1

    return result


def _analyze_code(code: str, language: str, filename: str) -> ExtractedCode:
    """Analyze extracted code for validity and metadata."""
    result = ExtractedCode(
        code=code,
        language=language,
        filename=filename,
        line_count=code.count("\n") + 1,
    )

    result.imports = _IMPORT_RE.findall(code)
    result.has_main_guard = 'if __name__' in code

    for pattern, warning in _DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            result.warnings.append(warning)

    if language == "python":
        try:
            ast.parse(code)
            result.is_valid = True
        except SyntaxError as exc:
            result.is_valid = False
            result.syntax_errors.append(
                f"Line {exc.lineno}: {exc.msg}" if exc.lineno else str(exc)
            )

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    result.classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not any(isinstance(p, ast.ClassDef) for p in ast.walk(tree)):
                        result.functions.append(node.name)
        except SyntaxError:
            pass

    elif language in ("html", "css", "javascript", "js"):
        result.is_valid = bool(code.strip())
    else:
        result.is_valid = bool(code.strip())

    if not result.has_main_guard and language == "python":
        result.warnings.append("No if __name__ == '__main__' guard found")

    return result


def _looks_like_code(text: str) -> bool:
    """Heuristic check if text looks like Python code."""
    indicators = [
        text.startswith("import "),
        text.startswith("from "),
        text.startswith("class "),
        text.startswith("def "),
        "def __init__" in text,
        "import tkinter" in text,
        "import customtkinter" in text,
        "from PyQt" in text,
        "from PySide" in text,
    ]
    return any(indicators)


def inject_main_guard(code: str) -> str:
    """Add a main guard to code that lacks one."""
    if 'if __name__' in code:
        return code

    lines = code.split("\n")
    class_pattern = re.compile(r"^class\s+(\w+)")
    app_class = None
    for line in lines:
        m = class_pattern.match(line)
        if m:
            app_class = m.group(1)

    guard = '\n\nif __name__ == "__main__":\n'
    if app_class:
        if "App" in app_class or "Window" in app_class or "Main" in app_class:
            guard += f"    app = {app_class}()\n    app.mainloop()\n"
        else:
            guard += f"    app = {app_class}()\n    app.mainloop()\n"
    else:
        guard += "    pass  # Add startup code here\n"

    return code + guard


def strip_markdown(response: str) -> str:
    """Remove markdown formatting from a response, keeping only code."""
    extracted = extract_code(response)
    return extracted.code if extracted.code else response


def get_required_packages(code: str) -> list[str]:
    """Determine pip packages needed for the code."""
    import_map = {
        "customtkinter": "customtkinter",
        "tkinter": None,
        "PyQt6": "PyQt6",
        "PySide6": "PySide6",
        "wx": "wxPython",
        "kivy": "kivy",
        "dearpygui": "dearpygui",
        "flet": "flet",
        "nicegui": "nicegui",
        "streamlit": "streamlit",
        "gradio": "gradio",
        "PIL": "Pillow",
        "cv2": "opencv-python",
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "plotly": "plotly",
        "requests": "requests",
        "psutil": "psutil",
    }

    imports = _IMPORT_RE.findall(code)
    packages: list[str] = []
    seen: set[str] = set()

    for imp in imports:
        top_level = imp.split(".")[0]
        if top_level in import_map and import_map[top_level] and top_level not in seen:
            packages.append(import_map[top_level])
            seen.add(top_level)

    return sorted(packages)
