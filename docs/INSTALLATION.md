# Installation and startup diagnostics

This source installation has been checked on the development PC. It is not yet a tested friend release. Use a writable folder and keep the source files together, including the hidden `.agents` folder. Another Windows account, another device, and a release ZIP still need their own verification.

## Install and open

Use Windows 11 x64 and **standard 64-bit CPython 3.14.x**, with Tcl/Tk, pip, and venv. The local checks used Python 3.14.3 and Tk 8.6. Other Python minor versions, ARM64, free-threaded builds, and the embeddable distribution are not supported by this installation path. The embeddable distribution omits components intended for an ordinary Python installation. See [Python on Windows](https://docs.python.org/3.14/using/windows.html).

Open PowerShell in the project folder:

```powershell
./setup.ps1
```

Setup selects an interpreter in this order: an explicit `-Python` path, an existing project `.venv`, installed Python 3.14 through `py.exe`, then `python.exe` from PATH if the launcher is absent. It prints the selection and validates it. If the selected interpreter fails, setup stops with repair advice. It does not try another interpreter or install Python automatically.

For an explicit choice, supply the full executable path:

```powershell
./setup.ps1 -Python 'C:/path/to/python.exe'
```

Setup creates or reuses `.venv` and installs the application dependencies there. Test dependencies are optional: use `./setup.ps1 -IncludeTests` for development. If an existing environment belongs to a different Python installation, setup asks you to use that interpreter or rename `.venv` as a backup before trying again. It does not overwrite that environment or remove personal data.

Open **launch.cmd** after setup. A successful launch opens only the companion. Without BG3, the panel says it is waiting for the game and starts with INPUT OFF. Opening it twice reports that a companion is already running for that runtime folder. Normal launch always uses the project environment.

## If PowerShell blocks a downloaded script

After checking that you trust the downloaded source, run this from the project folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

The policy setting applies to that PowerShell process, not the machine or your future sessions. Organization policy can still prevent execution; use your administrator's approved route in that case. The launcher uses the same process-scoped setting. See [Microsoft's execution-policy documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies).

## If setup or launch fails

Setup prints the error. Launch shows a Windows dialog, including failures before Tk or application dependencies can load. Both give a diagnostic log location, normally under `.runtime/logs`. If the project cannot store a log, the message identifies a log under `%TEMP%/BG3Companion`. If neither location is writable, it explicitly says no log could be written. Logs stay local and can contain local paths; inspect them before sharing.

| Failure | Next action |
| --- | --- |
| Python is missing or unsupported | Install standard 64-bit Python 3.14 with Tcl/Tk and pip, then select its executable with `-Python`. |
| Tk is missing or broken | Repair the selected Python with Tcl/Tk enabled and rerun setup. `py -3.14 -m tkinter` opens Python's installation-check window. |
| pip or venv is missing | Repair standard Python with pip and venv support. Do not substitute the embeddable distribution. |
| Dependency installation fails | Check the log, network, and package-index access, then rerun setup. |
| A folder is not writable | Restore access or move the complete source/data folder somewhere writable. Administrator launch is not required. |
| `.venv` is incomplete or belongs to another Python | Close the companion, rename `.venv` as a backup, and rerun setup with the intended Python. Keep `.runtime` and `play-sessions`. |
| A companion is already running | Use its existing window or close it before launching again. A process exit releases the launch lock automatically. |
| Source files or skills are missing | Restore the complete source folder, including hidden `.agents` files, and rerun setup. |

Python documents the Tk check in its [Tkinter reference](https://docs.python.org/3.14/library/tkinter.html).

For a structured report:

```powershell
./.venv/Scripts/python.exe -m bg3_helper doctor
```

The report includes versions, selected paths, required resources, writable-folder checks, and the installed Codex CLI's version/help capabilities. The folder probes create disposable temporary files. The report does not read saved conversation credentials, capture the screen, inspect game saves, send input, or queue a request. A successful CLI help probe does not prove that a conversation can answer. The report remains usable when application dependencies are missing.

Rerunning setup preserves history, screenshots, profiles, save references, and conversation settings. Close the companion before repairing dependencies. Setup never deletes or resets those records.

## Verification boundary

Current-machine checks on 2026-09-20 cover a new isolated environment in a path containing spaces, brackets, accented text, and Chinese characters; a second setup run preserving synthetic personal records; opt-in test dependency installation; rejection of installed Python 3.11; and the actual quiet launcher opening a waiting panel with INPUT OFF. A second launch was rejected and recorded with its log location. A synthetic failure visually confirmed the native dialog's repair advice and log location. Test launches use synthetic game-data folders and no conversation connection.

The full suite passed with 104 tests. New tests cover missing Python components/dependencies, unsupported interpreters, permissions, incomplete environments, pip failure, explicit interpreter mismatch, duplicate launch locking, log fallback, native notification failure, and quiet success versus visible failure reporting. Real PowerShell subprocess tests verify success and failure exit codes. Diagnostics tests check that only CLI version/help is used and raw subprocess error text is omitted. No BG3 capture, game input, or live Codex request is part of these checks.

Testing under a clean Windows account, on other devices, and against a release archive remains outstanding. Display portability and the friend-owned connection are separate board steps.
