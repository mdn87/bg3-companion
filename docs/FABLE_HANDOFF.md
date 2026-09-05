# Fable handoff

Paste the prompt below into Fable. It requests a plan grounded in the current local application, with no concurrent implementation edits. The absolute paths are intentional for this local handoff; the product itself must work under a friend's own username and installation path.

```text
Refine the BG3 Companion concept and source-beta plan into a practical implementation brief and prioritized backlog. This pass is planning only: another agent is developing the same application. Do not edit application files, change Git state, install dependencies, publish, run the companion/game, capture the desktop, or send game input.

Local project: C:\Users\Matt\Desktop\MyDocs\bg3-helper
GitHub: https://github.com/mdn87/bg3-companion
Existing interpreter: C:\Users\Matt\Desktop\MyDocs\bg3-helper\.venv\Scripts\python.exe

Read applicable AGENTS.md instructions and these documents:
C:\Users\Matt\Desktop\MyDocs\bg3-helper\docs\CONCEPT.md
C:\Users\Matt\Desktop\MyDocs\bg3-helper\docs\SOURCE_BETA_PLAN.md
C:\Users\Matt\Desktop\MyDocs\bg3-helper\docs\MODS_AND_SHARED_RUNS.md

Inspect current HEAD/status, README, setup/launch scripts, pyproject.toml, relevant source/tests, and repository skills read-only. The original review baseline was 3962a7d32282b7738ba84669a22b93887cebe1ca; reconcile newer work rather than assuming the plan is current. Do not inspect private .runtime, play-sessions, credentials, or actual game/save/mod folders for this planning pass. Use synthetic examples. If local access is unavailable, use the public repo and state the limits instead of claiming local verification.

Keep the Windows/Python/Tkinter app and existing codex queue connection. Friends use their own Codex conversation/account without a separate model API key. Ship a small source beta first; defer an executable. Preserve visible INPUT/STOP, bounded gestures, callback confirmation, cancellation, history, and explicit save references. Keep three editable setup profiles with Balanced selected and recorded overrides; profile application needs separate live validation. Tableforge is a source of future lessons, not a direct port.

Include the minimum mod/shared-run feature: read-only detection of configured entries and package-file presence, exact known versions/order, snapshots and changes since the previous scan, manual campaign/party/host notes, and a previewed copyable text report. Distinguish configured, file-present, unknown, and live-verified evidence. Never infer what is loaded from a save name or package filename. Reports exclude paths, tokens, save labels, and personal notes by default. Do not turn this into automatic mod management, save synchronization, cloud collaboration, or multiplayer input control. Friend-manifest import/comparison can follow the initial text report.

Return one cohesive brief containing: current readiness with commit and evidence; before-sharing versus later scope; coherent implementation batches with concrete files, dependencies, and acceptance criteria; first-user install/connect/callback/explain/input/action/STOP/restart checks plus mod-report/privacy tests; and only decisions that actually need Matt, with recommended defaults. Cite verified file paths/lines. Distinguish committed defects, temporary integration gaps, and untested proposals; never claim tests passed without observing them.

Finish with the smallest recommended first implementation batch and its handoff boundary with the active developer. Return the brief in the response; do not begin implementation or create issues/tasks automatically.
```

Target: Fable. The prompt keeps the current code and evidence central while separating a small source beta from later synchronization and packaging work.
