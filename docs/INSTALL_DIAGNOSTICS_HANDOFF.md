# Installation and visible diagnostics handoff

Prepared 2026-09-20. The installation step is implemented and merged into `main` through [PR #2](https://github.com/mdn87/bg3-companion/pull/2). Implementation commit: `311671d`; merge commit: `5993c58`.

## Completed scope

The selected board item was `bg3-companion:beta:install-diagnostics`. Its prerequisite was confirmed: capture, play history, setup profiles, and all three repository skills existed, and the original 70 tests passed before implementation.

- Setup selects and validates standard Windows x64 CPython 3.14.x. It checks Tcl/Tk, pip, venv, folder write access, required source resources, and installed dependencies.
- Interpreter selection prefers an explicit `-Python` path, then the existing project environment, then installed Python 3.14 through the Python launcher. PATH is considered only when the launcher is absent. A failed selection stops with advice; setup does not install Python or silently try another interpreter.
- Dependencies install inside `.venv`. Test tools require `-IncludeTests`. Setup reruns preserve personal records and reject incompatible or incomplete environments with recovery instructions.
- Normal launch requires the project environment and stays quiet on success. Failures show repair advice and a diagnostic log location. An OS file lock rejects duplicate launches for the same runtime folder.
- `doctor` reports versions, paths, required resources, write checks, and Codex CLI help capabilities. It works without application dependencies and does not capture the game, inspect saves, send input, queue a request, or read saved conversation credentials.

## Files to read

| File | Responsibility |
| --- | --- |
| [Installation guide](INSTALLATION.md) | Supported setup, interpreter selection, troubleshooting, and verification limits. |
| [setup.ps1](../setup.ps1) and [PowerShell helper](../scripts/bootstrap.ps1) | Interpreter selection, native-process handling, and reporting before Python can start. |
| [Python bootstrap](../bg3_helper/bootstrap.py) | Installation, guarded startup, native error notification, logs, and duplicate-launch locking. |
| [Diagnostics](../bg3_helper/diagnostics.py) | Dependency-free environment checks and CLI version/help inspection. |
| [Launcher](../launch.ps1) and [launch.cmd](../launch.cmd) | Quiet normal startup with no global-interpreter fallback. |
| [Startup tests](../tests/test_startup.py) | Failure scenarios and real PowerShell process-exit checks. |
| [Technical reference](../TECHNICAL.md) | Existing controls, command interface, safety contracts, and historical verification. |

## Recorded validation

These are results from the implementation session on 2026-09-20, not tests rerun while writing this handoff.

- The full suite passed: **104 tests**. Added coverage includes missing Python/components/dependencies, unsupported interpreters, permissions, pip failure, environment mismatch, duplicate launch, log fallback, native notification failure, and real PowerShell success/failure exit codes.
- An actual isolated installation succeeded in a folder containing spaces, brackets, accented text, and Chinese characters. A rerun preserved synthetic personal records. Test tools were absent by default and installed successfully when explicitly requested.
- Explicitly selecting installed Python 3.11 produced an actionable rejection and log location.
- The actual launcher opened a waiting panel with INPUT OFF and no persistent console. A second launch was rejected. A synthetic failure visually verified the native error dialog and log location.
- `doctor` passed local installation checks and found the installed CLI's required help flags. No conversation callback was tested.
- Both board files passed `parseChipFile` and `parseProjectStatusFile` exported by the Dias chip-board package. Every string is under 180 characters.

Tests used synthetic game-data locations. No game input or live Codex request was sent. Local screenshots and installation logs remain in ignored `.runtime/install-check`; they are not public release artifacts.

To repeat the automated suite from the project folder:

```powershell
New-Item -ItemType Directory -Force .runtime/test-temp | Out-Null
$env:PYTEST_DEBUG_TEMPROOT = "$PWD/.runtime/test-temp"
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m bg3_helper doctor
```

Use `./setup.ps1 -IncludeTests` if the selected project environment lacks pytest. Review the installation guide before changing an existing environment.

## Board state and next session

The installation chip is `done`, with one completion evidence entry. `.dias/status.json` points to `bg3-companion:beta:codex-connection`, titled **Friend-owned Codex connection with a test button**. That chip remains `ready`; its implementation has not started. The board's project-wide 15 percent assessment still carries its original September 5 date and was not recalculated.

When assigned the connection chip, start with [source beta plan, batch 2](SOURCE_BETA_PLAN.md#2-friend-owned-codex-connection), `bg3_helper/session.py`, `bg3_helper/panel.py`, and the session/transport tests. Reuse the new diagnostics where appropriate. The intended result is Connect/Test controls with distinct configured, queued, working, and callback-confirmed states. CLI help and queue acceptance do not prove a returned callback. Preserve request expiry, STOP cancellation, gesture limits, and the rule that an advice-only request cannot gain input permission later.

Clean-account installation, other-device checks, release-archive validation, display portability, and the complete friend-release exercise remain outstanding. The completed local installation work does not establish release readiness.

## Continuity notes

- The operator explicitly selected installation diagnostics, superseding the earlier installation deferral for this chip only. `AGENTS.md` records that scope decision.
- Draft PR #1 and the existing `rc/local-action-plan` worktree are separate planning work. Neither was merged or removed. Read their current state before using them as an implementation plan.
- The pre-existing `.lugos-wip/` directory was left untouched. Runtime state, captures, history, and local handoffs must remain out of Git.
- Native commands update PowerShell's global `LASTEXITCODE`. A local variable with that name hid successful exit codes; the helper now uses the global value, with regression tests for both success and failure.
- The desktop-control helper was unavailable during validation. Read-only remotedesk capture verified the waiting panel; local read-only capture verified the native dialog on another monitor. Temporary test processes were stopped afterward.
