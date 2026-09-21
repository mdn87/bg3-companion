"""Failure paths run without a game, input, live queue requests, or installers."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from bg3_helper import bootstrap, diagnostics


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Companion [test] \u00e9"
    root.mkdir()
    for name in ("setup.ps1", "launch.cmd", "launch.ps1", "scripts/bootstrap.ps1", "pyproject.toml",
                 "bg3_helper/bootstrap.py", "bg3_helper/panel.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    for skill in diagnostics.SKILLS:
        path = root / ".agents" / "skills" / skill / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("fixture", encoding="utf-8")
    return root


@pytest.fixture
def checked_environment(project, monkeypatch):
    info = diagnostics.interpreter_details()
    info.update(version_pair=[3, 14], version="3.14.3", implementation="CPython", platform="win32",
                machine="AMD64", bits=64, releaselevel="final", free_threaded=False)
    monkeypatch.setattr(diagnostics, "interpreter_details", lambda: info)
    monkeypatch.setattr(diagnostics, "check_tk", lambda: "8.6")
    monkeypatch.setattr(diagnostics, "check_pip", lambda: "25.3")
    monkeypatch.setattr(diagnostics, "check_venv", lambda: "available")
    return info


@pytest.mark.parametrize("change", [
    {"version_pair": [3, 11]}, {"version_pair": [3, 15]}, {"bits": 32},
    {"machine": "ARM64"}, {"implementation": "PyPy"}, {"free_threaded": True},
    {"releaselevel": "candidate"}, {"platform": "linux"},
])
def test_unsupported_interpreter_is_actionable(project, checked_environment, change):
    checked_environment.update(change)
    report = diagnostics.environment_report(project, dependencies=False, require_venv=False)
    with pytest.raises(diagnostics.DiagnosticError, match="CPython 3.14"):
        diagnostics.require_checks(report)


@pytest.mark.parametrize("name", ["Tk", "pip", "venv"])
def test_missing_python_component_has_repair_advice(project, checked_environment, monkeypatch, name):
    def missing():
        raise ImportError("private diagnostic detail")
    monkeypatch.setattr(diagnostics, "check_" + name.lower(), missing)
    report = diagnostics.environment_report(project, dependencies=False, require_venv=False)
    assert not report["ok"]
    assert "private diagnostic detail" not in json.dumps(report)
    failure = next(c for c in report["checks"] if c["name"] == name)
    assert "setup.ps1" in failure["remedy"]


def test_embeddable_distribution_is_rejected(project, checked_environment):
    checked_environment["base_executable"] = str(project / "python.exe")
    (project / "python314._pth").write_text(".")
    report = diagnostics.environment_report(project, dependencies=False, require_venv=False)
    with pytest.raises(diagnostics.DiagnosticError, match="embeddable"):
        diagnostics.require_checks(report)


def test_write_probe_exercises_directory_and_cleans_its_file(tmp_path):
    path = tmp_path / "new \u00e9 folder"
    assert diagnostics.check_writable(path) == str(path)
    assert list(path.iterdir()) == []
    file = tmp_path / "not-a-directory"
    file.write_text("keep")
    with pytest.raises(OSError):
        diagnostics.check_writable(file)
    assert file.read_text() == "keep"


def test_permission_and_missing_resources_are_reported(project, checked_environment, monkeypatch):
    def denied(path):
        raise PermissionError("private")
    monkeypatch.setattr(diagnostics, "check_writable", denied)
    report = diagnostics.environment_report(project / "missing", dependencies=False, require_venv=False)
    assert not report["ok"]
    assert any(c["name"] == "runtime write access" and not c["ok"] for c in report["checks"])
    assert any(c["name"].startswith("resource:") and not c["ok"] for c in report["checks"])
    assert "private" not in json.dumps(report)


def test_doctor_can_report_missing_dependencies_without_importing_panel(project, checked_environment, monkeypatch):
    real_import = diagnostics.importlib.import_module
    def without_dependencies(name):
        if name in diagnostics.DEPENDENCIES.values():
            raise ModuleNotFoundError(name)
        return real_import(name)
    monkeypatch.setattr(diagnostics.importlib, "import_module", without_dependencies)
    monkeypatch.setattr(diagnostics, "cli_capabilities", lambda: {"status": "unavailable"})
    monkeypatch.setitem(sys.modules, "bg3_helper.panel", None)
    report = diagnostics.doctor(project)
    assert not report["ok"]
    assert all(not c["ok"] for c in report["checks"] if c["name"] in diagnostics.DEPENDENCIES)
    assert not (project / ".runtime" / "connection.json").exists()
    assert not (project / "play-sessions" / "session.json").exists()


@pytest.mark.parametrize("flag_text,status", [
    ("--thread UUID --message TEXT --image PATH", "available"),
    ("--thread-id UUID --message TEXT --image PATH", "unsupported"),
])
def test_cli_probe_only_runs_help_and_redacts_output(monkeypatch, flag_text, status):
    from bg3_helper import session
    calls = []
    monkeypatch.setattr(session, "codex_command", lambda: ["codex.exe"])
    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["shell"] is False and kwargs["timeout"] == 10
        text = "codex-cli 0.153.2\nsecret-token" if command[-1] == "--version" else flag_text + "\nsecret-token"
        return subprocess.CompletedProcess(command, 0, text, "secret-token")
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    report = diagnostics.cli_capabilities()
    assert report["status"] == status
    assert report["connection_tested"] is False
    assert "secret-token" not in json.dumps(report)
    assert calls == [["codex.exe", "--version"], ["codex.exe", "queue", "--help"]]


def test_cli_probe_timeout_is_reported(monkeypatch):
    from bg3_helper import session
    monkeypatch.setattr(session, "codex_command", lambda: ["codex.exe"])
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("codex", 10)
    monkeypatch.setattr(diagnostics.subprocess, "run", timeout)
    assert diagnostics.cli_capabilities()["status"] == "timeout"


def test_startup_failure_has_native_notification_and_traceback(project, monkeypatch, capsys):
    messages = []
    def broken(*args, **kwargs):
        raise ImportError("missing native dependency")
    monkeypatch.setattr(bootstrap, "launch", broken)
    monkeypatch.setattr(bootstrap, "notify_failure", messages.append)
    assert bootstrap.guarded_launch(project / ".runtime", project=project) == 2
    logs = list((project / ".runtime" / "logs").glob("startup-*.log"))
    assert len(logs) == 1
    assert "Traceback" in logs[0].read_text()
    assert "missing native dependency" in logs[0].read_text()
    assert len(messages) == 1
    assert str(logs[0]) in messages[0] and "setup.ps1" in messages[0]
    assert "Diagnostic log:" in capsys.readouterr().err


def test_successful_launch_is_quiet(project, monkeypatch, capsys):
    messages = []
    monkeypatch.setattr(bootstrap, "launch", lambda *a, **k: print("library output"))
    monkeypatch.setattr(bootstrap, "notify_failure", messages.append)
    assert bootstrap.guarded_launch(project / ".runtime", project=project) == 0
    assert messages == []
    assert capsys.readouterr() == ("", "")


def test_no_log_access_still_displays_failure(project, monkeypatch):
    messages = []
    def denied(*args):
        raise PermissionError("denied")
    monkeypatch.setattr(bootstrap, "open_log", denied)
    monkeypatch.setattr(bootstrap, "notify_failure", messages.append)
    assert bootstrap.guarded_launch(project / ".runtime", project=project) == 2
    assert "No log could be written" in messages[0]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows notification")
def test_native_dialog_failure_is_not_silently_accepted(monkeypatch):
    import ctypes
    monkeypatch.setattr(ctypes.windll.user32, "MessageBoxW", lambda *args: 0)
    with pytest.raises(OSError, match="could not display"):
        bootstrap.notify_failure("fixture error")


def test_unwritable_project_logs_to_explicit_temporary_location(tmp_path, monkeypatch):
    project = tmp_path / "unwritable-project"
    project.write_text("not a directory")
    monkeypatch.setattr(bootstrap.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
    path, handle = bootstrap.open_log(project, "startup")
    with handle:
        handle.write("diagnostic")
    assert path.parent == tmp_path / "temp" / "BG3Companion"
    assert path.read_text() == "diagnostic"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file lock")
def test_duplicate_launch_is_rejected_and_lock_releases_after_error(tmp_path):
    with pytest.raises(RuntimeError):
        with bootstrap.instance_lock(tmp_path):
            with pytest.raises(diagnostics.DiagnosticError, match="already running"):
                with bootstrap.instance_lock(tmp_path):
                    pytest.fail("duplicate entered")
            raise RuntimeError("startup failed")
    with bootstrap.instance_lock(tmp_path):
        pass


def test_failed_checks_prevent_panel_import(project, monkeypatch):
    monkeypatch.setattr(diagnostics, "environment_report", lambda *a, **k: {
        "ok": False, "checks": [{"ok": False, "name": "Tk", "remedy": "Repair Python"}]})
    monkeypatch.setitem(sys.modules, "bg3_helper.panel", None)
    with pytest.raises(diagnostics.DiagnosticError, match="Repair Python"):
        bootstrap.launch(project, project / ".runtime")


@pytest.fixture
def installer(project, monkeypatch):
    monkeypatch.setattr(diagnostics, "environment_report", lambda *a, **k: {
        "ok": True, "checks": [], "python": {"version": "3.14.3"}})
    python = project / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("fake interpreter")
    calls = []
    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        stdout = json.dumps([str(project / ".venv"), sys.base_prefix]) if arguments[0] == "-c" else "ok"
        return subprocess.CompletedProcess(arguments, 0, stdout, "")
    monkeypatch.setattr(diagnostics, "run_python", run)
    return calls


@pytest.mark.parametrize("include_tests", [False, True])
def test_rerun_preserves_data_and_test_dependencies_are_opt_in(project, installer, include_tests):
    sentinels = [project / "play-sessions" / "profiles.json", project / ".runtime" / "session.json"]
    for path in sentinels:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"personal data")
    bootstrap.install(project, io.StringIO(), include_tests=include_tests)
    pip_call = next(args for args, kwargs in installer if args[:3] == ["-m", "pip", "install"])
    assert pip_call[-1] == str(project) + ("[test]" if include_tests else "")
    assert all(path.read_bytes() == b"personal data" for path in sentinels)
    assert not any(args[:2] == ["-m", "venv"] for args, kwargs in installer)


def test_pip_failure_is_actionable_and_stops_install(project, installer, monkeypatch):
    real_run = diagnostics.run_python
    def run(arguments, **kwargs):
        if arguments[:3] == ["-m", "pip", "install"]:
            return subprocess.CompletedProcess(arguments, 1, "", "failed https://user:secret@example.test/simple")
        return real_run(arguments, **kwargs)
    monkeypatch.setattr(diagnostics, "run_python", run)
    log = io.StringIO()
    with pytest.raises(diagnostics.DiagnosticError, match="network or package index"):
        bootstrap.install(project, log)
    assert "secret" not in log.getvalue()
    assert "--dependencies" not in str(installer)


def test_selected_python_cannot_silently_reuse_other_environment(project, installer, monkeypatch):
    monkeypatch.setattr(diagnostics, "run_python", lambda *a, **k: subprocess.CompletedProcess(
        [], 0, json.dumps([str(project / ".venv"), str(project / "other-python")]), ""))
    with pytest.raises(diagnostics.DiagnosticError, match="differs from the existing"):
        bootstrap.install(project, io.StringIO())


def test_partial_environment_is_preserved(project, checked_environment):
    environment = project / ".venv"
    environment.mkdir()
    marker = environment / "keep.txt"
    marker.write_text("existing installation")
    with pytest.raises(diagnostics.DiagnosticError, match="Rename it as a backup"):
        bootstrap.install(project, io.StringIO())
    assert marker.read_text() == "existing installation"


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell launcher")
def test_setup_reports_missing_explicit_python_in_literal_path(project):
    for relative in ("setup.ps1", "scripts/bootstrap.ps1"):
        shutil.copyfile(diagnostics.PROJECT / relative, project / relative)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(project / "setup.ps1"), "-Python", str(project / "missing-python.exe")],
                            capture_output=True, timeout=30)
    output = (result.stdout + result.stderr).decode(errors="replace")
    assert result.returncode == 1
    assert "selected Python executable does not exist" in output
    assert "Diagnostic log:" in output
    assert list((project / ".runtime" / "logs").glob("setup-launcher-*.log"))


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell launcher")
def test_setup_reports_no_python_without_installing_or_falling_back(project):
    for relative in ("setup.ps1", "scripts/bootstrap.ps1"):
        shutil.copyfile(diagnostics.PROJECT / relative, project / relative)
    shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(project / "setup.ps1")], capture_output=True, timeout=30,
                            env={**os.environ, "PATH": ""})
    output = (result.stdout + result.stderr).decode(errors="replace")
    assert result.returncode == 1
    assert "Python was not found" in output
    assert "Diagnostic log:" in output
    assert not (project / ".venv").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell launcher")
@pytest.mark.parametrize("native_exit", [0, 7])
def test_powershell_wrapper_preserves_real_python_exit_status(tmp_path, native_exit):
    script = tmp_path / "check-native.ps1"
    script.write_text("""param([string]$Helper, [string]$Python, [string]$Log, [int]$NativeExit)
. $Helper
$result = Invoke-CompanionPython -Executable $Python -Arguments @('-c', ('raise SystemExit({0})' -f $NativeExit)) -Log $Log -Quiet
exit $result
""", encoding="utf-8")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                             "-Helper", str(diagnostics.PROJECT / "scripts/bootstrap.ps1"),
                             "-Python", sys.executable, "-Log", str(tmp_path / "check.log"),
                             "-NativeExit", str(native_exit)], capture_output=True, timeout=30)
    assert result.returncode == native_exit, (result.stdout, result.stderr)
