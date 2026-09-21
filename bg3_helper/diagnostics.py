"""Installation checks that work before third-party packages are installed."""
from __future__ import annotations

import importlib
import importlib.metadata
import os
import platform
import re
import struct
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent
SUPPORTED_PYTHON = "standard 64-bit CPython 3.14.x for Windows (with Tcl/Tk and pip)"
SKILLS = ("bg3-observe", "bg3-smart-move", "bg3-system-setup")
DEPENDENCIES = {"mss": "mss", "Pillow": "PIL.ImageTk", "pywin32": "win32gui"}


class DiagnosticError(Exception):
    pass


def run_python(arguments, *, executable=None, timeout=30):
    return subprocess.run(
        [str(executable or sys.executable), *map(str, arguments)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, shell=False,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def interpreter_details():
    return {
        "executable": sys.executable, "version": platform.python_version(),
        "implementation": platform.python_implementation(), "platform": sys.platform,
        "machine": platform.machine(), "bits": struct.calcsize("P") * 8,
        "version_pair": list(sys.version_info[:2]), "releaselevel": sys.version_info.releaselevel,
        "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "prefix": sys.prefix, "base_prefix": sys.base_prefix,
        "base_executable": getattr(sys, "_base_executable", sys.executable),
    }


def supported_interpreter(info):
    return (info["implementation"] == "CPython" and info["platform"] == "win32"
            and info["version_pair"] == [3, 14] and info["releaselevel"] == "final"
            and info["bits"] == 64 and info["machine"].lower() in {"amd64", "x86_64"}
            and not info["free_threaded"])


def storage_paths(project, runtime=None, data=None, test_target=False):
    project = Path(project).resolve()
    runtime = Path(runtime).resolve() if runtime else project / ".runtime"
    data = (Path(data).resolve() if data else
            project / "play-sessions" if runtime == project / ".runtime" and not test_target
            else runtime / "play-sessions")
    return runtime, data


def check_writable(path):
    """Probe the real directory, including existing ACLs, with a disposable file."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=path) as probe:
        probe.write(b"BG3 Companion write check")
        probe.flush()
    return str(path)


def check_tk():
    # Use a child so Tk cannot initialize this process before Windows DPI setup.
    result = run_python(["-c", "import tkinter; r = tkinter.Tk(); r.withdraw(); "
                         "print(r.tk.call('info', 'patchlevel')); r.destroy()"])
    if result.returncode:
        raise DiagnosticError("Tcl/Tk could not open a window. Repair Python with Tcl/Tk enabled.")
    return result.stdout.strip()


def check_pip():
    result = run_python(["-m", "pip", "--version"])
    if result.returncode:
        raise DiagnosticError("pip is unavailable. Repair this interpreter with pip enabled.")
    match = re.search(r"^pip ([\w.+-]+)", result.stdout)
    if not match:
        raise DiagnosticError("pip returned an unexpected version response. Repair pip.")
    return match.group(1)


def check_venv():
    importlib.import_module("venv")
    ensurepip = importlib.import_module("ensurepip")
    return "venv available; bundled pip " + ensurepip.version()


def environment_report(project=PROJECT, *, runtime=None, data=None, test_target=False,
                       dependencies=True, require_venv=True):
    project = Path(project).resolve()
    runtime, data = storage_paths(project, runtime, data, test_target)
    info = interpreter_details()
    checks = []

    def check(name, function, remedy):
        try:
            detail = function()
            checks.append({"name": name, "ok": True, "detail": detail})
        except Exception as exc:
            checks.append({"name": name, "ok": False, "detail": type(exc).__name__, "remedy": remedy})

    checks.append({"name": "interpreter", "ok": supported_interpreter(info),
                   "detail": info["version"], "remedy": "Install " + SUPPORTED_PYTHON + "."})
    if require_venv:
        checks.append({"name": "project environment", "ok": Path(sys.prefix).resolve() == project / ".venv"
                       and sys.prefix != sys.base_prefix, "detail": sys.prefix,
                       "remedy": "Run setup.ps1, then use this project's launch.cmd or .venv interpreter."})
    base = Path(info["base_executable"]).parent
    checks.append({"name": "standard distribution", "ok": not any(base.glob("python*._pth")),
                   "detail": str(base), "remedy": "Use standard Python; the embeddable distribution is unsupported."})
    check("Tk", check_tk, "Repair the selected Python with Tcl/Tk enabled, then rerun setup.ps1.")
    check("pip", check_pip, "Repair the selected Python with pip enabled, then rerun setup.ps1.")
    check("venv", check_venv, "Install standard Python with venv and ensurepip; rerun setup.ps1.")
    for name, path in {"project": project, "runtime": runtime, "history": data}.items():
        check(name + " write access", lambda p=path: check_writable(p),
              "Choose a writable project/data folder, close conflicting software, and rerun setup.ps1.")
    if (project / ".venv").exists():
        check("environment write access", lambda: check_writable(project / ".venv"),
              "Restore write access to .venv, then rerun setup.ps1.")
    resources = ["setup.ps1", "launch.cmd", "launch.ps1", "scripts/bootstrap.ps1", "pyproject.toml",
                 "bg3_helper/bootstrap.py", "bg3_helper/panel.py"]
    resources.extend(f".agents/skills/{skill}/SKILL.md" for skill in SKILLS)
    for resource in resources:
        checks.append({"name": "resource: " + resource, "ok": (project / resource).is_file(),
                       "detail": str(project / resource),
                       "remedy": "Restore the complete source folder, including hidden .agents files."})
    if dependencies:
        for distribution, module in DEPENDENCIES.items():
            def inspect_dependency(d=distribution, m=module):
                importlib.import_module(m)
                return importlib.metadata.version(d)
            check(distribution, inspect_dependency, "Run setup.ps1 to install or repair project dependencies.")
    return {"ok": all(item["ok"] for item in checks), "python": info,
            "paths": {"project": str(project), "runtime": str(runtime), "history": str(data)},
            "checks": checks}


def require_checks(report):
    failures = [item for item in report["checks"] if not item["ok"]]
    if failures:
        raise DiagnosticError("\n".join(f"{item['name']}: {item['remedy']}" for item in failures))


def cli_capabilities():
    """Only version/help; never read the connection descriptor or queue a request."""
    try:
        from .session import codex_command
        command = codex_command()
        options = dict(capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=10, shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        version = subprocess.run(command + ["--version"], **options)
        help_result = subprocess.run(command + ["queue", "--help"], **options)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "remedy": "Codex CLI help timed out. Check the installed CLI."}
    except Exception:
        return {"status": "unavailable", "remedy": "Check the Codex CLI installation and project dependencies."}
    flags = {flag: bool(re.search(re.escape(flag) + r"(?=[\s,=]|$)", help_result.stdout))
             for flag in ("--thread", "--message", "--image")}
    match = re.search(r"\bcodex-cli (\d+\.\d+\.\d+[\w.+-]*)", version.stdout)
    return {"status": "available" if version.returncode == help_result.returncode == 0 and all(flags.values())
            else "unsupported", "executable": command[0], "version": match.group(1) if match else None,
            "queue_flags": flags, "connection_tested": False}


def doctor(project=PROJECT, *, runtime=None):
    report = environment_report(project, runtime=runtime)
    try:
        report["companion_version"] = importlib.metadata.version("bg3-helper")
    except importlib.metadata.PackageNotFoundError:
        report["companion_version"] = None
    report["codex"] = cli_capabilities()
    report["scope"] = "Installation and CLI help only; no game capture, input, or conversation request."
    return report
