# GUI Builder — Security Notes

## API Key Storage
- **Threat**: Plaintext API key exposure
- **Mitigation**: API key stored in separate `.api_key` file with `chmod 0o600` permissions (Unix). Excluded from config.json serialization. Supports `GEMINI_API_KEY` env var as alternative.
- **TODO (MEDIUM)**: Migrate to OS keychain (keyring library) for encrypted storage on all platforms.

## Code Execution Sandbox
- **Threat**: Generated code executing malicious operations (file deletion, network exfiltration, privilege escalation)
- **Mitigation**: `validate_code_safety()` scans for dangerous patterns before execution:
  - Blocks `os.system`, `subprocess.call/Popen/run`, `shutil.rmtree`, `os.remove`
  - Blocks `eval()` (unless `ast.literal_eval`), `exec()`, `__import__()`
  - Blocks dangerous imports: `ctypes`, `winreg`, `_winapi`
  - Runs preview in separate subprocess (process isolation)
  - Preview timeout kills runaway processes
- **TODO (HIGH)**: Add filesystem sandboxing — restrict subprocess to temp directory only.
- **TODO (MEDIUM)**: Add network sandboxing — option to block outbound connections from previews.

## Input Validation
- **Threat**: Prompt injection via description field
- **Mitigation**: User descriptions are embedded in structured prompts with explicit output format constraints. Gemini responses are parsed for code fences only — no instruction extraction from model output.
- **TODO (LOW)**: Add content-length limits on user inputs.

## Data at Rest
- **Threat**: Project files containing sensitive data
- **Mitigation**: Projects saved as JSON in user's AppData/config directory with standard OS permissions. No encryption applied to project files.
- **TODO (LOW)**: Add optional project encryption for sensitive codebases.

## Network Security
- **Threat**: MITM attacks on API calls
- **Mitigation**: google-genai library uses HTTPS/TLS by default. No custom certificate handling.

## Diagnostic Reports
- **Threat**: Accidental exposure of secrets in diagnostic output
- **Mitigation**: API key explicitly excluded from diagnostic reports. Config dump only includes safe fields.

## Dependency Audit
- **Packages**: google-genai, customtkinter, Pillow, psutil
- **Status**: All are well-maintained packages with no known CVEs as of 2026-04.
- **TODO (LOW)**: Add automated CVE checking via `pip audit`.

## Temporary Files
- **Threat**: Sensitive code persisting in temp directories
- **Mitigation**: PreviewRunner uses `tempfile.mkdtemp()` and cleans up via `cleanup()` on shutdown.
- **TODO (MEDIUM)**: Add periodic temp cleanup for crash recovery scenarios.
