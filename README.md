# BG3 Companion

A local, single-player helper for Windows on 4070pc. Play Baldur's Gate 3 on the main display and use Codex on another display. The companion captures the visible game window and exposes short, verified input gestures to the active agent session. It requires no KVM, HDMI duplication, game mod, or separate model API key.

## Source beta planning

This repository contains a working local prototype and a proposed friend beta. The [product concept](docs/CONCEPT.md), [source beta plan](docs/SOURCE_BETA_PLAN.md), and [mods/shared-run proposal](docs/MODS_AND_SHARED_RUNS.md) distinguish current behavior from required release work. Mod inventory and shared-run text reports are planned features, not implemented controls. A [Fable handoff prompt](docs/FABLE_HANDOFF.md) includes the local development paths. Publishing these documents does not mark the beta's acceptance checks complete.

## Start

The project environment is already installed on 4070pc. Open `launch.cmd` to start the companion. For a fresh installation, run `./setup.ps1` in PowerShell; it installs dependencies inside `.venv`.

1. Open BG3 and keep its window visible on the main display. Borderless/windowed mode is the first test target; exclusive fullscreen and HDR need game-specific testing.
2. Keep the companion and Codex on a different display.
3. Optionally enter what you are trying to do, then press **Explain screen** for advice or **Smart next move** for a suggested move. Each button captures the game and queues one request into the linked Codex conversation. Its answer appears in the companion.
4. To let **Smart next move** carry out a small move, turn the prominent **INPUT** switch on. Its green track, right-hand thumb, **INPUT ON** label, and remaining time show that permission is active. A smart request submitted with input on can perform up to three gestures, observing after each. If the next move is uncertain, it gives advice instead. The button returns focus from the companion to the game so input can work.
5. Turn the switch off or press **STOP** to cancel the current request and disable input. The gray track, left-hand thumb, and **INPUT OFF** label mean advice only. Enabling input alone does not choose or execute anything. The switch also supports keyboard focus with Space or Enter.
6. Use **Session & save** to name this play session and link a save reference. **History** shows its screenshots, requests, results, and setting observations. The companion remembers its window placement when closed.
7. **Profiles: Balanced** opens the three editable setup profiles. **Smart system setup** saves a system/config baseline and screenshot, then asks the session to audit or apply the selected profile. With INPUT OFF it gives advice; with INPUT ON it can perform up to twelve settings gestures, inspecting each result.

The buttons are the main controls. Optional shortcuts are **Ctrl+Alt+Numpad 0** for Capture only, **Ctrl+Alt+Numpad 1** to toggle input, and **Ctrl+Alt+Numpad 2** for STOP. Keep **Num Lock on**; these use the numeric keypad, not the top-row digits. **Capture only** and its hotkey save an image without requesting advice. The switch follows the actual input state after a button press, shortcut, STOP, or timeout; an unsuccessful enable attempt leaves it OFF.

The companion starts with actions off. Enabling them lasts ten minutes. An advice-only request cannot gain input permission if actions are enabled after submission. STOP permanently cancels that request even if actions are subsequently re-enabled; submit a new request to continue. Requests expire after five minutes and are never retried automatically.

This is a button-triggered assistant, with no continuous play or background model loop. The agent is instructed to avoid story choices, save/load, rest, and exit. These are reasoning instructions, not a semantic game-state detector; the bridge itself enforces target, focus, frame freshness, permission, cancellation, and the request's gesture limit. Save/load hotkeys and arbitrary text/chords are not exposed.

## Play history and save references

Normal play data lives in ignored `play-sessions/`, separate from the temporary connection descriptor. Each dated play folder contains `session.json`, an append-only `events.jsonl`, and `captures/`, `requests/`, and `settings/` folders. Captures retain the full image, model preview, capture time, window dimensions, request ID, selected save reference, and settings snapshot ID. A Smart next move captures before queuing, and each gesture adds another screenshot and result. The History dialog previews those records and can open their folder.

**Session & save** can start or resume a play session and associate either a detected local `.lsv` file or a manual name. Discovery reads names, timestamps, sizes, and revision identifiers; it does not parse, load, rename, or change game saves. Selecting a save records its metadata at that moment. The newest file is never assumed to be the loaded save. STOP or finish an active request before changing its session or save link; switching sessions turns input off and requires a new capture.

On upgrade, old loose `.runtime/captures/` images and metadata are copied once into the initial play folder, marked as imported with no assumed save association. The originals remain intact. Retention is manual: nothing automatically deletes older screenshots. Use `panel --data PATH` to choose another storage root; only one companion should write to that root at a time. A non-default runtime gets its own `play-sessions/` folder by default.

## Setup profiles

Balanced is the default for companion development on 4070pc. All three profiles are editable starter preferences, not measured performance presets:

| Profile | Desired game frame cap | Resolution preference | Upscaling preference |
| --- | --- | --- | --- |
| Balanced | 60 FPS | Keep current | Keep current |
| Higher frame rate | 120 FPS | Keep current | DLSS Quality |
| Image quality | 60 FPS | Match the game display | DLAA |

All three start with borderless mode, background audio, and mouse movement between displays enabled. Unchecking the borderless preference leaves the current display mode alone. The other two checkboxes request their stated on/off behavior. **Save profile** persists differences from the starter values, a revision number, and your override note; **Starter defaults** fills the form for a reset, which must then be saved. Profile edits apply to the next setup request. An in-progress request retains its original profile and note.

**Read current settings** saves a read-only baseline without sending a model request or game input. It records display/GPU information, the target window, a copy of `graphicSettings.lsx`, raw config values, and explicitly observed menu settings. Configured game resolution and window/capture dimensions are separate: the first BG3 check had a saved 2560 × 1440 resolution and a 3840 × 2160 borderless client. Saved config can lag the menu; numerical settings enums are retained without guessing their meaning.

Smart system setup records visible before/after values and applies supported differences through the game menu when authorized. If settings cannot be identified or the twelve-gesture budget runs out, its result states what was verified and what remains. It does not claim FPS gains without measurements, replace a running game's config, or change Windows display settings, drivers, mods, or saves. This first version does not benchmark FPS automatically.

The reusable workflows live in `.agents/skills/bg3-observe`, `bg3-smart-move`, and `bg3-system-setup`. Button prompts point to the exact skill file, so they also work when the linked Codex conversation starts in the parent MyDocs workspace. A Codex task opened in this repository can discover these as [repository skills](https://learn.chatgpt.com/docs/build-skills).

## Connecting the buttons

The companion uses the installed `codex queue` command to send requests to an existing Codex conversation. It uses that conversation's model and account limits; no separate model API or API key is configured. Keep Codex available. When the conversation is busy, a request can wait for the active turn to finish. This is not a latency guarantee for real-time gameplay.

When launched from Codex, the companion remembers `CODEX_THREAD_ID` in ignored `.runtime/session.json`. Later launches reuse that link. To change it, run `connect THREAD_UUID` below. A saved link means a destination is configured; only a returned result confirms that the session answered. `request connection_test` sends a request without capturing or enabling input.

## Session commands

Run these from this project directory, using the project Python interpreter:

```powershell
./.venv/Scripts/python.exe -m bg3_helper doctor
./.venv/Scripts/python.exe -m bg3_helper status
./.venv/Scripts/python.exe -m bg3_helper capture
./.venv/Scripts/python.exe -m bg3_helper note "My advice from the active session."
./.venv/Scripts/python.exe -m bg3_helper stop
./.venv/Scripts/python.exe -m bg3_helper connect THREAD_UUID
./.venv/Scripts/python.exe -m bg3_helper request connection_test
./.venv/Scripts/python.exe -m bg3_helper history --limit 20
./.venv/Scripts/python.exe -m bg3_helper saves
./.venv/Scripts/python.exe -m bg3_helper play rename --label "4070pc development"
./.venv/Scripts/python.exe -m bg3_helper play link --name "Before the grove" --note "Manual reference"
./.venv/Scripts/python.exe -m bg3_helper profiles
./.venv/Scripts/python.exe -m bg3_helper settings-snapshot
./.venv/Scripts/python.exe -m bg3_helper settings
```

`profiles --profile-id balanced --overrides JSON --note "..."` saves override values. Supported keys are `target_fps`, `resolution`, `upscaling`, `borderless`, `background_audio`, and `unlock_mouse`. `settings-observe --frame FRAME_ID --values JSON --note "Before setup"` records values read from a screenshot belonging to the current play session. `request setup` submits the selected setup profile; each request captures its profile revision and starting evidence.

Button requests tell the receiving session to run `claim REQUEST_ID` first and stop if the request was cancelled, expired, or replaced. The session uses `finish REQUEST_ID --text "Result"` to return advice to the panel. While handling a smart request, every action must include `--smart-request REQUEST_ID`; a missing or stale ID is rejected.

`capture` returns JSON with `frame_id`, `preview_path`, `full_path`, the physical window rectangle, preview size, UTC capture time, and capture duration. Open `preview_path` with the agent's image-viewing tool. For small tooltips, inspect `full_path` or request a crop in **full-resolution** coordinates:

```powershell
./.venv/Scripts/python.exe -m bg3_helper crop 100 100 600 300
```

Actions use **pixels in the returned preview image**, not cropped-image coordinates, native screen coordinates, or the small preview shown in the companion. Replace the example ID and coordinates with values from a just-inspected frame:

```powershell
./.venv/Scripts/python.exe -m bg3_helper act move --frame FRAME_ID --x 700 --y 400 --request-id hover-1
./.venv/Scripts/python.exe -m bg3_helper act click --frame NEW_FRAME_ID --x 700 --y 400 --button left --request-id click-1
./.venv/Scripts/python.exe -m bg3_helper act key --frame NEW_FRAME_ID --key i --request-id inventory-1
./.venv/Scripts/python.exe -m bg3_helper act scroll --frame NEW_FRAME_ID --x 700 --y 400 --steps -1 --request-id scroll-1
```

Every action needs the latest frame and a new request ID. Retry an uncertain **identical** request with the **same** ID: it returns the original result without repeating input. A successful transport result is `input_sent`, not a claim that the intended game action succeeded. Inspect the returned `after.preview_path`. `outcome_unknown` disables input and exits with code 3; re-observe before doing anything else. Other rejected requests exit with code 2.

## Capture and input constraints

- Targets are recognized by `bg3.exe` or `bg3_dx11.exe`. Multiple matching windows, minimized windows, and windows extending outside the desktop are rejected.
- MSS captures the visible client region at native resolution. The bridge checks for unrelated windows overlapping that region; transparent, layered, non-activating cursor/highlight overlays are excluded from that check and can appear in captured pixels. It cannot see behind occlusion and does not promise atomic isolation from an overlay appearing during capture.
- Physical coordinates support scaling and monitors with negative origins. Preview coordinates map back to the recorded client rectangle. A moved/resized/replaced target invalidates the frame.
- Actions require input enabled, target focus, a frame at most 60 seconds old, and a visual recheck. A large scene change rejects the action; this check is conservative and does not prove that small objects or tooltips are unchanged. Animations can cause rejection.
- A user press of **Smart next move** or **Smart system setup** with actions allowed can return focus from the companion to the game. If focus has moved to another app, the companion leaves it alone and reports an error. Other capture/control commands do not activate windows.
- Input uses Windows `SendInput` and releases keys/buttons within the gesture. It rejects user-held modifiers/buttons. No elevation is requested; if the game runs at a higher privilege level, Windows may reject input.
- The panel's STOP and global stop hotkey remain available while a capture is running. They prevent subsequent gestures; they cannot retract an input batch Windows already accepted.
- The local bridge binds only `127.0.0.1` on an ephemeral port. Its per-session capability stays in ignored `.runtime/connection.json`; browser-origin requests are rejected. Input can only be enabled from the native panel or hotkey, not over HTTP.
- Full images, previews, metadata, actions, and button results stay in ignored `play-sessions/` for normal play. Do not commit captures or the connection descriptor.
- A queued preview is also attached to the linked Codex conversation for model analysis. The session takes a fresh capture before deciding or acting.

If a screenshot is black, washed out, obscured, or stale, stop before acting. Exclusive fullscreen capture, HDR color, and gameplay interactions still need validation on this machine; the DX11 borderless menu check below passed. A later Windows Graphics Capture/DXGI backend can replace MSS if needed.

## Implementation and Tableforge relationship

`windows.py` owns native targeting, capture, physical coordinates, and input. `core.py` owns frame identity, freshness, action validation, and results. `session.py` queues button requests and enforces their lifecycle and gesture budget. `history.py` keeps play sessions and save associations; `settings.py` keeps profiles, baselines, and menu observations. `transport.py` provides a local authenticated command interface; `panel.py`, `dialogs.py`, and `__main__.py` are its human/session surfaces. BG3 process detection and game key choices are specific to this prototype.

Future Tableforge work can reuse the observation/action/result contracts, display handling, interruption behavior, and validation lessons. Tableforge should use its own application state and semantic commands where available. This prototype is not a direct Tableforge port, and no Tableforge, Aire, Fade, or remotedesk code/configuration was changed.

Existing Aire depends on Comet capture. Fade's current Aire endpoint only submits a continuation prompt, so this prototype does not claim to use that endpoint for general game input. Its capture approach follows the existing remotedesk MSS/Pillow path, with game-window targeting and full-desktop coordinates added independently.

## Verification

Open `launch-dev.cmd` for the disposable arena plus a separate **BG3 Companion — Test** window. It keeps its own profiles and history under `.runtime/test-panel/` and uses a fake game-data location, so it does not inspect real saves or graphics config. It copies only the normal companion's conversation destination for testing Explain/Smart buttons. Capture, profiles, history, and baseline inspection also work without a model connection. Global shortcuts can belong to only one running companion; use buttons if the normal panel already owns them. Close the test companion and reopen the launcher after code edits to load the new code.

```powershell
New-Item -ItemType Directory -Force .runtime/test-temp | Out-Null
$env:PYTEST_DEBUG_TEMPROOT = "$PWD/.runtime/test-temp"
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m bg3_helper.test_arena
```

The disposable arena's **Run bridge self-test** button exercises actual software capture, one mouse click, one key press, one scroll, and duplicate suppression. It writes before/after screenshots and `result.json` to `.runtime/self-test/`. No game/save is used. To connect a separate companion to it, use an isolated runtime:

```powershell
./.venv/Scripts/python.exe -m bg3_helper --runtime .runtime/test-panel panel --test-target
```

Tests use a fake desktop for negative monitor coordinates, frame invalidation, input policy, duplicate/uncertain results, local HTTP behavior, request cancellation/expiration, advice-only permissions, and gesture limits. They also cover session restart/switching, explicit save revisions, legacy capture import, profile override persistence, frozen setup requests, and setting observations tied to their original frames. Test request senders are mocked; pytest never queues a live conversation request or sends OS input.

Live BG3 check, 2026-09-05: DX11 in borderless mode passed a menu capture and click test on 4070pc. The complete 3840 × 2160 client capture and a native crop were readable. Two bridge clicks opened Audio and unchecked **Mute Sound When Inactive**. A subsequent capture with the companion focused still showed it unchecked. Captures took approximately 0.8–1.0 seconds. Screenshots and the result record are under ignored `.runtime/captures/` and `.runtime/acceptance/audio-background.json`.

The first click was correctly rejected while Codex had focus; activating BG3 through the Windows tool allowed the fresh-frame retry. This tested direct session commands, not a Smart next move button request. Audible background playback, settings persistence across game restart, and gameplay actions were not measured.

Session/profile checks, 2026-09-05: 70 automated tests and all three skill validators passed. Native UI checks verified profile saving, history image previews, session switching, persisted window placement, and the isolated development launcher through Windows PowerShell. Six earlier game captures were copied into the first play session. A later fresh capture was correctly refused while Chrome covered part of BG3; the audio observation retains the original screenshot's timestamp. A complete setup-button round trip and live profile application still need a menu run with the game unobscured.

Native implementation references: [MSS capture examples](https://python-mss.readthedocs.io/latest/examples.html), [Windows DPI awareness](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext), and [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput).
