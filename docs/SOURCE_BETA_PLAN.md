# First shareable Windows source beta

Status: implementation plan, not a claim of release readiness. Updated 2026-09-05.

## Baseline and evidence

The planning inspection used commit `3962a7d32282b7738ba84669a22b93887cebe1ca` on `main`. The checkout was clean and had no remote; `mdn87/bg3-companion` was public and empty. Those are pre-publication observations: this documentation publication will add the remote and push the reviewed source history. Recheck HEAD, the working tree, and concurrent development before implementing the plan.

The baseline already includes screenshot/play history, explicit save references, setup snapshots, three profiles with overrides, and three repository skills. Mod inventory and shared-run reporting are proposals, not existing features.

The [README's verification record](../README.md#verification) reports earlier automated and native UI checks. This planning pass did not rerun those tests or operate the companion/game. The recorded direct BG3 menu clicks were not a full Smart next move button round trip. Setup-button completion, live profile application, audible background playback, settings persistence across a game restart, and gameplay input remain distinct validation gaps. No uncommitted temporary integration problem was observed in the inspected baseline.

Confirmed implementation gaps include PATH-dependent setup, potentially invisible normal-launch errors, source-relative callback resources that do not work as an ordinary wheel installation, a panel taller than a typical 1080p display, and missing release/CI/license metadata. These are separate from unverified live workflows.

## Intended beta

Target a small group of Windows friends who already use Codex, with a source ZIP and editable local installation. Keep the current Python/Tkinter application and button-triggered Codex integration. Proposed release version: `0.1.0b1`; proposed tag: `v0.1.0b1`. Publishing this plan is not creating that release.

Recommend Windows 11 x64 and standard CPython 3.14.x for the first tested installation path. The inspected environment is Python 3.14.3 with Tk 8.6; package metadata currently advertises Python >=3.11. Align support claims with the CI/manual matrix rather than assuming every advertised interpreter has been tested. The installed dependencies were mss 10.1.0, Pillow 12.2.0, and pywin32 311. Their presence in the developer environment does not establish a fresh installation result.

The initial live-game evidence is DX11 borderless at 3840 x 2160 on 4070pc. Document that separately from intended support and from untested Vulkan, exclusive fullscreen, HDR, other GPUs, and mixed-DPI configurations. Shared-run support initially means mod/setup reporting and notes; live input remains a single-player feature.

## Required delivery batches

These requirements precede the friend beta. They are ordered for implementation; files marked new do not exist in the inspected baseline.

### 1. Installation and visible diagnostics

**Files:** `setup.ps1`, `launch.cmd`, `pyproject.toml`, `bg3_helper/__main__.py`; add a small startup/diagnostics module if needed.

**Observed:** [setup.ps1, line 3](https://github.com/mdn87/bg3-companion/blob/3962a7d32282b7738ba84669a22b93887cebe1ca/setup.ps1#L3) uses `python` from PATH, creates `.venv`, and installs `.[test]`; it checks exit codes but offers generic errors. [launch.cmd, line 3](https://github.com/mdn87/bg3-companion/blob/3962a7d32282b7738ba84669a22b93887cebe1ca/launch.cmd#L3) detaches `pythonw` or falls back to global Python. The current `doctor` command primarily discovers game windows.

**Change:** select and validate a supported interpreter, check Tk/pip/venv and directory writability, make test dependencies opt-in, and use literal-path-safe PowerShell operations. Keep successful normal launch quiet, but show a useful failure message and diagnostic log path. Avoid a silent global-interpreter fallback. Document a process-scoped remedy for downloaded-script execution restrictions without changing machine-wide policy. Standard Python is required; do not use the embeddable distribution for this installation.

**Accept:** clean-account install works in a writable path with spaces and Unicode; missing Python/Tk, unsupported Python, pip failure, permission errors, and duplicate launch have actionable outcomes. Launch without BG3 opens a useful waiting state. Re-running setup preserves personal data. `doctor` reports versions, selected paths, required resources, and CLI capabilities without capture, input, or credential disclosure. Python documents `python -m tkinter` as an installation check. [Python Tkinter documentation](https://docs.python.org/3.14/library/tkinter.html)

### 2. Friend-owned Codex connection

**Files:** `bg3_helper/session.py`, `bg3_helper/panel.py`, `bg3_helper/__main__.py`, `tests/test_session.py`, `tests/test_transport.py`.

**Observed:** [session.py, line 20](https://github.com/mdn87/bg3-companion/blob/3962a7d32282b7738ba84669a22b93887cebe1ca/bg3_helper/session.py#L20) resolves a native CLI or a particular npm-shim layout, queues with `--thread`, `--message`, and optional `--image`, and validates a saved conversation UUID without proving a callback. Local `codex-cli 0.153.2` exposes the required flags. That is an observed version, not a minimum supported release. The [public CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli) inspected did not establish a minimum version for `queue`.

**Change:** add Connect and Test connection controls, a capability probe, and distinct configured/queued/working/callback-confirmed states. Give a friend a documented way to link their own local task and account, including a path that does not require finding an undocumented UUID in the app UI. The task must be able to read the project/skills/captures and execute the local bridge CLI with its ordinary permissions. Do not introduce a separate API key or require optional desktop-control plugins.

**Accept:** a text-only connection test completes via `claim` and `finish` with "Connected. Companion buttons can reach this session." No capture/input occurs. Missing CLI or flags, invalid/unavailable destinations, and callback failures are distinguishable. Queue acceptance is not completion and does not prove the task was busy. Keep five-minute request expiry, no automatic retry after uncertain delivery, and STOP cancellation. Delayed requests cannot act after cancellation/expiry or gain input permission retroactively. A busy conversation is tested with an actual delayed callback.

### 3. Distribution and display portability

**Files:** `bg3_helper/session.py`, `bg3_helper/panel.py`, `bg3_helper/dialogs.py`, all three `.agents/skills/*/SKILL.md` files, related tests, `README.md`.

**Observed:** [callback paths](https://github.com/mdn87/bg3-companion/blob/3962a7d32282b7738ba84669a22b93887cebe1ca/bg3_helper/session.py#L215) derive the source root from `__file__`, then point to `.venv\Scripts\python.exe` and `.agents\skills`. [pyproject.toml](../pyproject.toml) packages only `bg3_helper*`. A normal wheel therefore cannot satisfy these callback/resource assumptions; no wheel was built in this review. An extracted ZIP plus editable installation is the intended path but needs independent clean-install validation. [Panel sizing](https://github.com/mdn87/bg3-companion/blob/3962a7d32282b7738ba84669a22b93887cebe1ca/bg3_helper/panel.py#L48) requires at least 1,180 pixels of height, and saved placement does not ensure every control fits a changed work area.

**Change:** explicitly support and validate the source layout. Include setup/launch scripts, metadata, application code, hidden `.agents` skill files, docs/license when chosen, and tests in the release archive; exclude the author's virtual environment. Update skills to use current frame dimensions and only documented companion capabilities. If focus cannot be returned safely, ask the player to refocus and retry rather than assuming an optional Windows-control tool exists. Make the body/dialogs responsive or scrollable, keep INPUT/STOP visible, and clamp saved placement to the current work area.

**Accept:** callbacks and skill reads work from a freshly extracted source ZIP under another account. Missing resources produce a useful error. The UI fits 1080p at 100%, 125%, and 150% scaling; negative origins, mixed DPI, and monitor removal are checked. Existing coordinate tests do not substitute for these live checks.

### 4. Session history and credible setup profiles

**Files:** `bg3_helper/history.py`, `bg3_helper/settings.py`, `bg3_helper/dialogs.py`, `bg3_helper/session.py`, `tests/test_history_settings.py`, `.agents/skills/bg3-system-setup/SKILL.md`.

**Change:** preserve the existing explicit save associations and evidence-linked history. Keep Balanced selected and all three editable profiles, including override notes. The other starter profiles currently suggest DLSS/DLAA; do not treat those settings as applicable to every GPU. Missing NVIDIA tooling must not prevent ordinary use. Ship setup auditing/recommendations first unless a full live setup application sequence is independently verified; the current implementation can apply settings when INPUT is on, so audit-only beta scope requires an explicit change or feature gate, not just wording.

**Accept:** overrides, associations, observations, and screenshots survive restart. Saved config values remain distinct from live observations and configured resolution from capture dimensions. Unknown settings stay unknown; unsupported options are left unchanged with an explanation. Setup never claims FPS gains without measurement or changes mods, drivers, saves, or OS display settings. If profile application is included, record before/after evidence and verify persistence across a game restart.

### 5. Read-only mod inventory and shared-run text

**Files:** proposed `bg3_helper/mods.py` and `tests/test_mods.py`; integrate with `bg3_helper/history.py`, `bg3_helper/dialogs.py`, `bg3_helper/panel.py`, and `bg3_helper/__main__.py`. Keep report formatting near its data contract; avoid a new service/framework.

**Change:** implement the minimum described in [Mods and shared runs](MODS_AND_SHARED_RUNS.md): select a profile, inspect saved mod configuration and package-file presence, snapshot evidence, show changes since the previous scan, retain manual run/party notes, and copy a reviewed plain-text summary. Use the current configurable game-data location. The first comparison is between this machine's own snapshots; importing a friend's manifest can follow.

**Accept:** preserve configured/file-present/unknown distinctions and exact version values; never equate a `.pak` filename with an active mod or a selected save with loaded game state. Missing or unreadable sources do not become empty verified lists. Scans are bounded, off the UI thread, and write only companion history. They capture no screen, send no model request, and require no INPUT. Shared previews exclude local paths, credentials, save labels, and personal notes by default. Synthetic-fixture and restart tests pass. A human can use two friends' copied lists to identify a known difference, without a compatibility guarantee or automatic modification.

### 6. Privacy, retention, and updates

**Files:** `.gitignore`, `README.md`, proposed `docs/PRIVACY_AND_UPDATES.md`; targeted history tests for documented update/cleanup behavior.

**Observed:** `.runtime/`, `play-sessions/`, and local handoff files are ignored. Normal history stores full images/previews, request/results data, explicit save metadata, settings observations, and copied graphics config. Captures use absolute artifact paths. Save association records file metadata rather than copying the save. Requested previews go to Codex, and the agent may inspect full images/crops/context too.

**Change:** disclose the local-to-Codex data flow before first analysis and distinguish Capture only, deterministic mod inspection, copy/export, and model requests. Retain data until manual removal for the first beta; disclose growing storage and provide a careful backup/removal procedure. Keep a stable user-writable installation folder and document a code-only update that preserves personal data. Regenerate transient bridge credentials; never restore armed input or replay requests. Expand ignore rules for local environment files, builds, logs/support bundles, and personal exports. Later move data outside the installation tree with a deliberate migration and relative artifact paths.

**Accept:** the documented update preserves sessions, images, save references, notes, profiles, and mod snapshots. Restart leaves INPUT off. Copy/export uses a field allowlist and has a preview. Release archives exclude runtime tokens, conversation links, captures, saves, real inventory reports, raw game/config backups, and personal notes. Review tracked files and reachable history before initial publication; `.gitignore` does not sanitize an arbitrary working-folder ZIP. Explain that local deletion does not delete screenshots already submitted to Codex.

### 7. Release presentation and verification

**Files:** `README.md`, `pyproject.toml`, proposed `LICENSE`, `CHANGELOG.md`, `.github/workflows/windows.yml`; focused additions to `tests/`.

**Change:** put concise setup/connect/use instructions first, followed by troubleshooting and a tested/untested matrix. Add project URLs, readme/license metadata after the owner decides, Windows classifiers, and matching beta version/tag/release notes. Run Windows CI with declared test dependencies, mocked Codex senders, no game, and no credentials. Verify extracted source-archive contents and fresh editable installation. Validate shipped skills without depending on a validator installed only on Matt's machine.

**Accept:** the relevant mocked test suite, startup/capability tests, mod-fixture tests, and source-archive checks pass in Windows CI. A friend completes the manual sequence below against the exact archive. Release notes identify limitations and update/data instructions. Create the prerelease only after these gates, not merely because the plan or source has been pushed.

## First-time-user release test

1. **Install:** use a clean Windows account, standard supported Python, and the release ZIP extracted into a writable path with spaces/Unicode. Borrow no developer environment, runtime state, or conversation link.
2. **Launch:** double-click, confirm reachable controls and INPUT OFF. Confirm a useful waiting state without BG3 and actionable startup diagnostics.
3. **Connect:** open a dedicated local Codex task, verify CLI capabilities, and select that friend's conversation/account.
4. **Receive callback:** run the text-only connection test and receive the exact connection acknowledgement in the panel. Verify no image or game input.
5. **Capture/explain:** with INPUT OFF and BG3 unobscured, request advice. Confirm readable image, returned explanation, matching history records, and no gesture.
6. **Enable INPUT:** confirm the switch only grants permission; it initiates no work.
7. **One verified action:** request exactly one reversible menu action such as opening Audio. Verify one gesture, the after-image, and the completion callback. No external desktop plugin should be needed for the supported button flow.
8. **STOP:** cancel a queued or working request. Confirm immediate local input revocation and rejection of a late action, even after manually enabling INPUT again. Also test a busy task, expiry, double press, and uncertain delivery without automatic replay.
9. **Restart:** name a play session, link a save explicitly, save a profile override/note, then restart. Confirm all history and metadata persist, INPUT is off, and no request resumes. Repeat after the documented code update.
10. **Mods/shared run:** select a game profile, refresh its read-only inventory, add optional run notes, inspect a previous-scan difference, and copy the preview. Confirm no game files changed, no Codex request was sent, and excluded private fields are absent. Exchange reports manually with another friend or use two synthetic reports to verify differences and unknowns remain clear.

## Improvements after the first beta

- AppData or another stable personal-data root, relative artifact references, and versioned migrations.
- Storage usage, retention controls, and redacted diagnostic exports.
- Import/compare path-free friend manifests; optional package hashing and additional mod-source adapters.
- Broader GPU/rendering/Python/display coverage, measured performance work, and verified profile application.
- A Windows executable if source installation is a recurring obstacle. Start with one-folder packaging, bundled skill resources, and a proper CLI callback entry point. A frozen executable is not a Python interpreter accepting the current `-m` command. [PyInstaller runtime documentation](https://pyinstaller.org/en/stable/runtime-information.html)

No cloud synchronization, automatic mod installation, continuous play, or second-player agent control is required for this release.

## Owner decision and completion rule

The unresolved owner decision is the license and copyright identity; MIT is recommended for the companion's code. Do not silently choose it or imply a license is already present. Source publication is not the tested beta release.

Other recommended defaults: a public prerelease for a small friend cohort, source ZIP, Balanced selected, manual retention, explicit shared-report preview, and setup auditing until live application is verified.

The beta is ready when Windows CI and one friend's complete sequence pass against the same reviewed archive without developer repairs between steps. Record actual results, commit, dependency versions, and tested configuration; do not convert a test definition or an earlier README statement into a new passing result.
