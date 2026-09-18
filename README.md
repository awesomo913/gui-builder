# GUI Builder

> Describe a GUI in plain English and get runnable Python code back — no drag-and-drop, no node graphs.

GUI Builder is a desktop app that turns a text description into working GUI code using the Gemini API, then lets you preview and iterate on it in a sandboxed runner before you ship it.

## Features
- `generate` command: turn a plain-English description into GUI code, with a chosen framework/style/components
- `template` command: start from a built-in template instead of a blank description
- Live preview sandbox that runs generated code in a locked-down subprocess — blocks dangerous calls like `os.system`, `subprocess.run`, and `shutil.rmtree`, and blocked imports like `ctypes`/`winreg`
- Code extraction/cleanup from raw Gemini responses (`code_extractor.py`)
- Project manager and persistent config, including a `set-key` command for your Gemini API key
- Diagnostics report generator for troubleshooting

## Stack
Python, CustomTkinter, Google Gemini API (`google-genai`), Pillow, psutil.

## Getting started
**Requirements**
- Python 3.10+
- A Gemini API key (set with `gui_builder set-key <key>`)

**Run**
```bash
pip install -r requirements.txt
python -m gui_builder generate "a login form with dark mode"
# or: python -m gui_builder template <template_id>
```

## Status
**Unmaintained / archived.** Personal project, published as-is — fork it, adapt it, take it over. No support or guarantees.

## License
[MIT](LICENSE) — free to use, fork, and build on.
