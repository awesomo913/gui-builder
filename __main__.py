"""GUI Builder entry point — CLI interface for the backend."""

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__, __app_name__
from .backend import GUIBuilderBackend
from .code_extractor import extract_code


def main() -> int:
    """CLI entry point for GUI Builder."""
    parser = argparse.ArgumentParser(
        prog="gui_builder",
        description=f"{__app_name__} v{__version__} — AI-powered GUI generation",
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    gen_p = sub.add_parser("generate", help="Generate a GUI from a description")
    gen_p.add_argument("description", help="Description of the GUI to generate")
    gen_p.add_argument("-f", "--framework", default=None, help="Target framework")
    gen_p.add_argument("-s", "--style", default="modern", help="Visual style")
    gen_p.add_argument("-o", "--output", default=None, help="Output file path")
    gen_p.add_argument("-c", "--components", nargs="*", help="Components to include")

    tmpl_p = sub.add_parser("template", help="Generate from a template")
    tmpl_p.add_argument("template_id", help="Template ID")
    tmpl_p.add_argument("-f", "--framework", default=None)
    tmpl_p.add_argument("-s", "--style", default="modern")
    tmpl_p.add_argument("-o", "--output", default=None)

    list_p = sub.add_parser("list", help="List available resources")
    list_p.add_argument("resource", choices=["templates", "components", "styles", "frameworks", "projects", "models"])

    check_p = sub.add_parser("check", help="Check code for syntax and imports")
    check_p.add_argument("file", help="Python file to check")

    preview_p = sub.add_parser("preview", help="Run a preview of generated code")
    preview_p.add_argument("file", help="Python file to preview")
    preview_p.add_argument("-t", "--timeout", type=int, default=30000, help="Timeout in ms")

    diag_p = sub.add_parser("diagnostics", help="Generate diagnostic report")

    config_p = sub.add_parser("config", help="View or update configuration")
    config_p.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), action="append")
    config_p.add_argument("--show", action="store_true")

    key_p = sub.add_parser("set-key", help="Set the Gemini API key")
    key_p.add_argument("key", help="Your Gemini API key")

    test_p = sub.add_parser("test-connection", help="Test Gemini API connection")

    refine_p = sub.add_parser("refine", help="Refine existing GUI code")
    refine_p.add_argument("file", help="Python file to refine")
    refine_p.add_argument("feedback", help="What to change")
    refine_p.add_argument("-o", "--output", default=None)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    backend = GUIBuilderBackend()

    if args.command == "set-key":
        ok, msg = backend.set_api_key(args.key)
        print(msg)
        return 0 if ok else 1

    if args.command == "test-connection":
        ok, msg = backend.test_connection()
        print(msg)
        return 0 if ok else 1

    if args.command == "diagnostics":
        report, path = backend.run_diagnostics()
        print(report)
        if path:
            print(f"\nSaved to: {path}")
        backend.shutdown()
        return 0

    if args.command == "config":
        if args.show or not args.set:
            for key, value in sorted(vars(backend.config).items()):
                if key != "api_key":
                    print(f"  {key}: {value}")
        if args.set:
            updates = {}
            for key, value in args.set:
                try:
                    updates[key] = json.loads(value)
                except json.JSONDecodeError:
                    updates[key] = value
            issues = backend.update_settings(**updates)
            if issues:
                for issue in issues:
                    print(f"  WARNING: {issue}")
            print("Configuration updated")
        backend.shutdown()
        return 0

    if args.command == "list":
        if args.resource == "templates":
            for t in backend.get_templates():
                print(f"  [{t.id}] {t.name} — {t.description}")
        elif args.resource == "components":
            for name, desc in backend.get_components().items():
                print(f"  {name}: {desc}")
        elif args.resource == "styles":
            for name, desc in backend.get_styles().items():
                print(f"  {name}: {desc}")
        elif args.resource == "frameworks":
            for name, desc in backend.get_frameworks().items():
                print(f"  {name}: {desc}")
        elif args.resource == "projects":
            for p in backend.list_projects():
                mod = time.strftime("%Y-%m-%d", time.localtime(p["modified"]))
                print(f"  {p['name']} ({p['framework']}) — {p['file_count']} files — {mod}")
        elif args.resource == "models":
            if not backend.is_connected:
                print("Not connected. Set your API key first: gui_builder set-key YOUR_KEY")
                return 1
            for m in backend.client.list_models():
                print(f"  {m}")
        backend.shutdown()
        return 0

    if args.command == "check":
        code = Path(args.file).read_text(encoding="utf-8")
        result = backend.check_code(code)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        backend.shutdown()
        return 0 if result.success else 1

    if args.command == "preview":
        code = Path(args.file).read_text(encoding="utf-8")
        backend._preview._timeout_ms = args.timeout
        result = backend._preview.run_preview(code, blocking=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        backend.shutdown()
        return 0 if result.ok else 1

    if not backend.is_connected:
        print("Not connected. Set your API key first:")
        print("  python -m gui_builder set-key YOUR_KEY")
        backend.shutdown()
        return 1

    if args.command == "generate":
        done = {"finished": False, "result": None, "error": None}

        def on_complete(extracted):
            done["result"] = extracted
            done["finished"] = True

        def on_error(msg):
            done["error"] = msg
            done["finished"] = True

        print(f"Generating {args.framework or backend.config.default_framework} GUI...")
        backend.generate_gui(
            description=args.description,
            framework=args.framework,
            style=args.style,
            components=args.components,
            on_complete=on_complete,
            on_error=on_error,
        )

        while not done["finished"]:
            time.sleep(0.1)

        if done["error"]:
            print(f"Error: {done['error']}", file=sys.stderr)
            backend.shutdown()
            return 1

        extracted = done["result"]
        if args.output:
            Path(args.output).write_text(extracted.code, encoding="utf-8")
            print(f"Saved to: {args.output}")
        else:
            print(extracted.code)

        if extracted.warnings:
            for w in extracted.warnings:
                print(f"  WARNING: {w}", file=sys.stderr)

        backend.shutdown()
        return 0

    if args.command == "template":
        done = {"finished": False, "result": None, "error": None}

        def on_complete(extracted):
            done["result"] = extracted
            done["finished"] = True

        def on_error(msg):
            done["error"] = msg
            done["finished"] = True

        print(f"Generating from template: {args.template_id}...")
        backend.generate_from_template(
            template_id=args.template_id,
            framework=args.framework,
            style=args.style,
            on_complete=on_complete,
            on_error=on_error,
        )

        while not done["finished"]:
            time.sleep(0.1)

        if done["error"]:
            print(f"Error: {done['error']}", file=sys.stderr)
            backend.shutdown()
            return 1

        extracted = done["result"]
        if args.output:
            Path(args.output).write_text(extracted.code, encoding="utf-8")
            print(f"Saved to: {args.output}")
        else:
            print(extracted.code)

        backend.shutdown()
        return 0

    if args.command == "refine":
        code = Path(args.file).read_text(encoding="utf-8")
        done = {"finished": False, "result": None, "error": None}

        def on_complete(extracted):
            done["result"] = extracted
            done["finished"] = True

        def on_error(msg):
            done["error"] = msg
            done["finished"] = True

        print("Refining code...")
        backend.refine_gui(
            feedback=args.feedback,
            current_code=code,
            on_complete=on_complete,
            on_error=on_error,
        )

        while not done["finished"]:
            time.sleep(0.1)

        if done["error"]:
            print(f"Error: {done['error']}", file=sys.stderr)
            backend.shutdown()
            return 1

        extracted = done["result"]
        output = args.output or args.file
        Path(output).write_text(extracted.code, encoding="utf-8")
        print(f"Saved to: {output}")
        backend.shutdown()
        return 0

    parser.print_help()
    backend.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
