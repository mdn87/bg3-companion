"""Dependency-free setup and guarded GUI startup, also runnable as a file."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
import uuid

if __package__:
    from . import diagnostics
else:
    import diagnostics


def open_log(project, purpose):
    filename = f"{purpose}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.log"
    for directory in (Path(project) / ".runtime" / "logs", Path(tempfile.gettempdir()) / "BG3Companion"):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            return path, path.open("a", encoding="utf-8")
        except OSError:
            continue
    raise diagnostics.DiagnosticError("Cannot write a diagnostic log in the project or temporary folder. Restore write access.")


def notify_failure(message):
    import ctypes
    if not ctypes.windll.user32.MessageBoxW(None, message, "BG3 Companion could not start", 0x10010):
        # Let the PowerShell wrapper report a native dialog failure itself.
        raise OSError("Windows could not display the startup error dialog.")


@contextmanager
def instance_lock(runtime):
    """An OS-released file lock rejects simultaneous launches before any data writes."""
    import msvcrt
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "panel.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise diagnostics.DiagnosticError(
                "A companion is already running for this runtime folder. Use its window or close it before launching again."
            ) from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def checked_python(arguments, log, failure, *, executable=None, timeout=600):
    try:
        result = diagnostics.run_python(arguments, executable=executable, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise diagnostics.DiagnosticError(f"{failure} ({type(exc).__name__}).") from None
    # Installer output can include private index URLs. Redact URL userinfo.
    import re
    output = result.stdout + result.stderr
    output = re.sub(r"(https?://)[^\s/@]+:[^\s/@]+@", r"\1[redacted]@", output)
    log.write(output + "\n")
    log.flush()
    if result.returncode:
        raise diagnostics.DiagnosticError(f"{failure} (exit {result.returncode}).")
    return result


def install(project, log, *, include_tests=False):
    project = Path(project).resolve()
    report = diagnostics.environment_report(project, dependencies=False, require_venv=False)
    log.write(json.dumps(report, indent=2) + "\n")
    diagnostics.require_checks(report)
    print(f"Selected Python: {sys.executable} ({report['python']['version']})")
    environment = project / ".venv"
    python = environment / "Scripts" / "python.exe"
    if environment.exists():
        if not python.is_file():
            raise diagnostics.DiagnosticError(
                "The existing .venv is incomplete. Rename it as a backup, then rerun setup.ps1. Personal data is preserved."
            )
        probe = checked_python(["-c", "import json, sys; print(json.dumps([sys.prefix, sys.base_prefix]))"],
                               log, "Cannot use the existing .venv. Rename it as a backup and rerun setup.ps1",
                               executable=python, timeout=30)
        prefix, base = json.loads(probe.stdout)
        if Path(prefix).resolve() != environment or Path(base).resolve() != Path(sys.base_prefix).resolve():
            raise diagnostics.DiagnosticError(
                "The selected Python differs from the existing .venv. Use its original Python or rename .venv as a backup and rerun setup.ps1."
            )
    else:
        print("Creating the project environment...")
        checked_python(["-m", "venv", str(environment)], log,
                       "Could not create .venv. Check write access and repair Python's venv/pip installation")
    checked_python([str(project / "bg3_helper" / "bootstrap.py"), "check"], log,
                   "The project environment failed validation. Repair Python or rename .venv as a backup and rerun setup.ps1",
                   executable=python, timeout=60)
    print("Installing companion dependencies" + (" and test tools..." if include_tests else "..."))
    checked_python(["-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-e",
                    str(project) + ("[test]" if include_tests else "")], log,
                   "pip could not install dependencies. Check the network or package index and rerun setup.ps1",
                   executable=python)
    checked_python([str(project / "bg3_helper" / "bootstrap.py"), "check", "--dependencies"], log,
                   "Installed dependencies failed validation. Review this log and rerun setup.ps1", executable=python,
                   timeout=60)
    print("Setup complete. Open launch.cmd to start BG3 Companion.")


def launch(project, runtime, *, data=None, test_target=False):
    report = diagnostics.environment_report(project, runtime=runtime, data=data, test_target=test_target)
    print(json.dumps(report, indent=2), flush=True)
    diagnostics.require_checks(report)
    with instance_lock(runtime):
        sys.path.insert(0, str(project))
        from bg3_helper.panel import run_panel
        run_panel(Path(runtime).resolve(), test_target, data=data)


def guarded_launch(runtime, *, data=None, test_target=False, project=diagnostics.PROJECT):
    log_path = None
    try:
        log_path, log = open_log(project, "startup")
        with log, redirect_stdout(log), redirect_stderr(log):
            try:
                launch(project, runtime, data=data, test_target=test_target)
            except Exception:
                traceback.print_exc()
                raise
        return 0
    except Exception as exc:
        if isinstance(exc, diagnostics.DiagnosticError):
            reason = str(exc)
        else:
            reason = f"Startup failed ({type(exc).__name__}). Review the log; run setup.ps1 if application files or dependencies are missing."
        location = f"Diagnostic log: {log_path}" if log_path else "No log could be written. Check project and temporary-folder write access."
        message = reason + "\n\n" + location
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        notify_failure(message)
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("setup", "check", "panel"))
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--dependencies", action="store_true")
    args = parser.parse_args()
    project = diagnostics.PROJECT
    if args.operation == "panel":
        return 20 if guarded_launch(project / ".runtime") else 0
    if args.operation == "check":
        report = diagnostics.environment_report(project, dependencies=args.dependencies)
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1
    log_path = None
    try:
        log_path, log = open_log(project, "setup")
        with log:
            try:
                install(project, log, include_tests=args.include_tests)
            except Exception:
                traceback.print_exc(file=log)
                raise
        print(f"Diagnostic log: {log_path}")
        return 0
    except Exception as exc:
        print(f"Setup failed: {exc}\nDiagnostic log: {log_path or 'unavailable; check folder write access'}", file=sys.stderr)
        return 20  # Distinguish a reported failure from an interpreter/loader error.


if __name__ == "__main__":
    raise SystemExit(main())
