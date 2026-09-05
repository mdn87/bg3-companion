# Local release-candidate action plan

Status: draft plan; implementation items have not started. Updated 2026-09-05.

This is the current implementation scope. It supersedes the installation and other-device testing priorities in the earlier [source beta proposal](SOURCE_BETA_PLAN.md). The target is the existing Windows/Python/Tkinter companion on 4070pc, using its existing environment. Friend installation remains proposed functionality. Do not spend this milestone rewriting setup instructions, creating fresh installations, testing another device, building an executable, or establishing a Python/GPU support matrix.

## Checkpoint and delivery

The requested README checkpoint was committed and pushed to `main` as `47ba1e4e039099290523db958d8dbd73dbce57ec` before this plan was created. Application code is still based on `3962a7d32282b7738ba84669a22b93887cebe1ca`. This plan belongs on the separate `rc/local-action-plan` branch and a draft release-candidate PR. The active developer's normal checkout remains on `main`.

The PR establishes the work boundaries; it does not claim that the features below are implemented or that a friend beta is ready. Keep it draft while implementation remains outstanding. No release tag, automatic merge, live game action, or work dispatch is part of publishing this plan.

## What we borrowed from Lugos

Autowork supplies the useful shape: bind a work item to a base commit, list allowed files, state contracts to preserve, define concrete steps and verification, and record how it finishes. Orca separates advisory planning from the authority to execute. We use that distinction here: the manifest is a task description, not an admitted worker assignment.

Read-only reference inspection found these files clean at their recorded commits:

| Local reference | Revision | Applied idea |
| --- | --- | --- |
| `C:\Users\Matt\Desktop\MyDocs\lugos\autowork\src\autowork\campaign\lap\schemas\plan.schema.json` | `272425683f19f462196ec9da6992a34f18b8a308` | Base commit, allowed files, expected contracts, verification references, completion/landing fields. |
| `C:\Users\Matt\Desktop\MyDocs\lugos\autowork\README.md` | Same Autowork revision | A task, write area, and structured verification commands are supplied before an assignment is prepared. |
| `C:\Users\Matt\Desktop\MyDocs\lugos\autowork\src\autowork\campaign\execution_plan.py` | Same Autowork revision | Execution decisions are bound to actual assignments. Do not invent assignment IDs or provider/target decisions in a planning document. |
| `C:\Users\Matt\Desktop\MyDocs\lugos\lugos-orca\config\task-envelope.schema.json` | `f71f1c42ec2fdb1b36386d613361d74e2ede18bf` | Objective, capabilities, deliverables, data classification, external actions, and argv-based verification. |
| `C:\Users\Matt\Desktop\MyDocs\lugos\lugos-orca\README.md` | Same Orca revision | Orca advises; Autowork admits and executes. A plan does not launch work. |

No Lugos code/configuration was changed and no Lugos job, provider, or agent was started. [local-rc-work-items.json](local-rc-work-items.json) is a BG3-specific planning format, not an Autowork/Orca input schema. If Autowork is used later, select one item, resolve its actual workspace and verification commands, and use Autowork's supported request producer. Do not dispatch this manifest as a handwritten request.

## Work sequence

The manifest owns the exact file boundaries, dependencies, acceptance criteria, and verification references. The table is a readable index.

| Item | Result | Depends on |
| --- | --- | --- |
| RC-01 | Useful local startup/connection diagnostics without setup or installation work. | None |
| RC-02 | A usable panel with Connect/Test controls, honest callback status, and size/focus guidance based on actual captures. | RC-01 |
| RC-03 | Readable history with explicit damage warnings and intact original records. | None |
| RC-04 | Deterministic, read-only mod inventory and snapshots with precise unknowns. | RC-03 |
| RC-05 | Manual run/party notes and a previewed, copyable shared-run summary. | RC-02, RC-04 |
| RC-06 | Clear settings-audit behavior and an evidence-backed local RC closeout. | RC-01 through RC-05 |

Start with RC-01. Follow the suggested sequence with one writer; dependency independence is not permission to launch parallel edits. RC-03 does not technically require RC-01, but keeping a single sequence avoids shared-file collisions and extra coordination.

## One-item execution contract

1. Select one item. Record its actual base commit, worktree, owner, and start time before writing. Reconcile newer commits and existing edits; do not discard another developer's work. A changed commit alone does not require renewed approval when the target and authorized scope are unchanged.
2. Give that owner the whole listed files for the duration of the item. Several items touch `panel.py`, `dialogs.py`, `session.py`, or `transport.py`; do not divide these files into simultaneous line ranges for different agents.
3. Use only the item's file list and preserve its stated contracts. Create proposed files only when that item starts. Local test output belongs under the worktree's ignored `.runtime/`; private play data and game folders are not test fixtures.
4. Run the referenced local checks after the coherent change. `{python}` means a verified existing project interpreter; `{worktree}` means that item's actual checkout. Substitute whole argv values, never shell-built command text. Prove imports come from the intended checkout before testing a worktree with the original environment.
5. Finish with a commit, changed-file list, observed verification results, unmet criteria, and any remaining risks. Mark `verified` only for acceptance actually demonstrated. Record skipped live checks explicitly. Hand back to the root; selecting the next item is a separate assignment.

If a failure repeats, record what changed between attempts and reassess within the same scope instead of looping blindly. Estimates and repair counts are advisory, not reasons to request approval by themselves. Stop the item when required access is absent, another writer owns the same files, or completion requires a materially different target/action such as game-file modification, remote execution, automatic mod changes, or installation work. Preserve the work and report the concrete reason; do not reset or clean it away.

No worker can gain capture/input permission from this plan. Verification uses mocked desktop/sender data and synthetic mod files. Any later live game check is separately selected by the operator; this PR does not run one.

## Corrections retained from the Fable review

- A damaged line currently fails a requested history read. Recover readable records with a visible count/warning, retaining the original bytes; silent skipping would hide missing evidence.
- HTTP authentication errors already have a distinct handler. Improve descriptor/network/response diagnostics without replacing existing authentication or game-input error messages with generic failures.
- Queue success and a stored UUID do not prove a returned callback. Say configured/queued until the matching request completes.
- Text, paths, and inspected context can reach Codex as well as screenshots. Do not publish a "screenshots only" privacy claim. Credential values are never an optional shared-report field.
- Full setup-button/profile application remains unverified even on 4070pc. Audit-first behavior requires code that enforces it, not a label claiming prior validation.
- A paths helper does not migrate absolute references in existing history. Data migration, wheel support, automatic pruning, and diagnostic archives are later work.
- No copyright name or license has been selected. That decision does not block the current local planning checkpoint.

## Local verification and RC meaning

The manifest's verification catalog uses the existing project interpreter and mocked tests only. Add tests for new behavior when implementing the relevant item; do not create dummy tests merely to satisfy the catalog now. Pure layout tests can simulate 1080p/1440p work areas, scaling, and negative monitor origins without another machine. They do not establish live support on those devices.

After implementation, the root reviews the complete diff once and runs the full relevant mocked suite on 4070pc. It checks the exact PR commit and tracked artifact list. Results from earlier reviews remain attributed to those reviews, not relabeled as new evidence. No hosted CI, fresh-install experiment, or other-device validation is a gate for this local milestone; future distribution checks stay in the source beta proposal.

Record these fields for each finished item, in the PR or a small evidence note: item ID, owner, base/result commits, files changed, command argv, exit codes and summaries, demonstrated acceptance, outstanding/manual checks, and next eligible item. Never include tokens, real saves, captured images, raw game configuration, or actual personal mod reports in public evidence.

The root may mark the RC implemented only when RC-01 through RC-06 are verified against this local scope. The draft planning PR alone is not completion of those items. Packaging, polished installation instructions, source-ZIP installation tests, license selection for distribution, other-device checks, cloud/save/mod synchronization, and multiplayer input remain deferred.
