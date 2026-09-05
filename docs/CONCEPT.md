# BG3 Companion: product concept

Status: proposed source beta, not a release announcement. Updated 2026-09-05.

BG3 Companion helps a Windows player understand the game in front of them, take one small action when requested, and remember the context of a playthrough. It also helps friends prepare a shared run by making their local setup and chosen campaign details easy to describe and compare.

The first audience is friends who already use Codex. They play BG3 on their main display and keep this Python/Tkinter companion on another display. They use their own Codex conversation and account. There is no separate model API key, KVM, duplicated video feed, or required game mod.

## The everyday experience

| Control or view | What the player gets | Scope |
| --- | --- | --- |
| Explain screen | A fresh screenshot and an explanation returned to the panel. | Advice, with no game input. |
| Smart next move | One useful, bounded move, with a new observation after each gesture. | At most three gestures when INPUT was enabled for that request. Otherwise advice. |
| INPUT and STOP | An obvious permission switch and an immediate way to cancel further gestures. | Turning INPUT on does not start work. Startup and restart leave it off. STOP does not undo input already accepted by Windows. |
| Session & save / History | Captures, requests, results, observations, and explicit save references associated with a named play session. | A selected save is a reference, not proof of which save is currently loaded. |
| Smart system setup / Profiles | A record of current settings and three editable preferences, including override notes. | Balanced by default. Audit first; live application remains a separate validation gate. |
| Mods & run summary (proposed) | A detected configuration list, changes since a previous scan, and a copyable text summary with optional campaign/party notes. | Read-only inspection and user-controlled sharing. No mod installation or synchronization. |

The shared-run feature is preparation and record keeping. It does not turn the companion into a second player, control another person's PC, or establish that live input is safe in a multiplayer session. The initial live-input support target remains single-player; the complete button workflow still needs the delivery plan's validation. Friends can exchange reports manually before entering BG3's own multiplayer/mod verification flow.

## Three useful journeys

1. **Get help now:** press Explain, read the result, optionally enable INPUT and request one small menu action, inspect the result, then STOP.
2. **Resume a personal run:** select the named play session, review the explicit save reference and last notes, inspect recent screenshots, and see the profile overrides chosen for this machine.
3. **Prepare to play together:** refresh the local mod inventory, select the relevant game profile and shared-run label, review what was actually detected, and copy a text summary for friends. Keep local machine preferences distinct from mod/game details that may affect a shared run. A future comparison can identify differences; neither a list nor a match guarantees compatibility.

"Personal context" initially means user-entered campaign, character/party, host alias, next objective, and setup notes, plus existing explicit save/settings associations. It does not mean automatically extracting character inventories, reading process memory, or inferring character progress from save filenames. Sensitive or spoiler-bearing notes are excluded from shared output unless selected in its preview.

## Product boundaries

- Preserve the Windows/Python/Tkinter application and its local observation/action/result interface.
- Keep model work button-triggered and bounded. A busy Codex task can delay a request; there is no real-time latency promise or continuous-play loop.
- Keep capture/input local while clearly disclosing that requested screenshots and inspected context go to Codex for analysis.
- Record evidence, timestamps, source, and uncertainty. A configuration file describes saved configuration; an image describes one visible moment.
- Make setup and failures understandable to a friend without an agent repairing their installation.
- Keep mod inspection deterministic and local. Copying a report does not require Codex or a model call.
- Share descriptions and references, not saves, mod packages, credentials, or automatic messages to friends.
- Do not build a new web app, cloud account system, automatic mod manager, or executable installer for this first release.

The future Tableforge connection is learning from session organization, evidence-linked advice, interrupted actions, and user-visible permissions. It is not a direct code or UI port; Tableforge should use its own application state and semantic operations where available.

## Delivery references

- [Source beta plan](SOURCE_BETA_PLAN.md): observed baseline, priorities, file changes, and release acceptance.
- [Mods and shared runs](MODS_AND_SHARED_RUNS.md): the proposed inventory and reporting contract.
- [Fable handoff](FABLE_HANDOFF.md): a local-path prompt for refining this into implementation tasks.

The concept is deliberately larger than what is currently verified. The delivery plan distinguishes implemented code, unverified workflows, and new proposals.
