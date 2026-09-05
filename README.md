# BG3 Companion

A local, single-player helper for Windows on 4070pc. Play Baldur's Gate 3 on the main display and use Codex on another display. The companion captures the visible game window and exposes short, verified input gestures to the active agent session. It requires no KVM, HDMI duplication, game mod, or separate model API key.

## Start

The project environment is already installed on 4070pc. Open `launch.cmd` to start the companion. For a fresh installation, run `./setup.ps1` in PowerShell; it installs dependencies inside `.venv`.

1. Open BG3 and keep its window visible on the main display. Borderless/windowed mode is the first test target; exclusive fullscreen and HDR need game-specific testing.
2. Keep the companion and Codex on a different display.
3. Ask Codex to capture the game and help with what is visible. The agent runs the capture command, reads the returned image, and replies in the conversation. It can also write advice into the companion panel.
4. For delegated input, enable input in the companion or press **Ctrl+Alt+F9**, then return focus to BG3. The bridge never steals focus. **Ctrl+Alt+F12** or **STOP** disables input.

**Ctrl+Alt+F8** captures without switching focus. A hotkey capture saves an image locally; it does **not** wake an idle Codex session or generate advice by itself. Ask for analysis in the conversation. There is no continuous video processing, background model loop, or implemented automatic tactical decision-making in this version.

The companion starts with input off. Enabling it lasts ten minutes; the agent still needs a specific delegated action. The implementation supports a single move, click, short key press, or scroll followed by an observation. Save/load hotkeys and arbitrary text/chords are not exposed.

## Session commands

Run these from this project directory, using the project Python interpreter:

```powershell
./.venv/Scripts/python.exe -m bg3_helper doctor
./.venv/Scripts/python.exe -m bg3_helper status
./.venv/Scripts/python.exe -m bg3_helper capture
./.venv/Scripts/python.exe -m bg3_helper note "My advice from the active session."
./.venv/Scripts/python.exe -m bg3_helper stop
```

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
- Input uses Windows `SendInput` and releases keys/buttons within the gesture. It rejects user-held modifiers/buttons. No elevation is requested; if the game runs at a higher privilege level, Windows may reject input.
- The panel's STOP and global stop hotkey remain available while a capture is running. They prevent subsequent gestures; they cannot retract an input batch Windows already accepted.
- The local bridge binds only `127.0.0.1` on an ephemeral port. Its per-session capability stays in ignored `.runtime/connection.json`; browser-origin requests are rejected. Input can only be enabled from the native panel or hotkey, not over HTTP.
- Full images, previews, metadata, and action records stay in ignored `.runtime/captures/`. Each capture stores both images and retention is manual for now. Do not commit captures or the connection descriptor.

If a screenshot is black, washed out, obscured, or stale, stop before acting. DirectX fullscreen capture, HDR color, and actual BG3 input acceptance must be validated on this machine. A later Windows Graphics Capture/DXGI backend can replace MSS if needed.

## Implementation and Tableforge relationship

`windows.py` owns native targeting, capture, physical coordinates, and input. `core.py` owns frame identity, freshness, action validation, and results. `transport.py` provides a local authenticated command interface; `panel.py` and `__main__.py` are its human/session surfaces. BG3 process detection and game key choices are specific to this prototype.

Future Tableforge work can reuse the observation/action/result contracts, display handling, interruption behavior, and validation lessons. Tableforge should use its own application state and semantic commands where available. This prototype is not a direct Tableforge port, and no Tableforge, Aire, Fade, or remotedesk code/configuration was changed.

Existing Aire depends on Comet capture. Fade's current Aire endpoint only submits a continuation prompt, so this prototype does not claim to use that endpoint for general game input. Its capture approach follows the existing remotedesk MSS/Pillow path, with game-window targeting and full-desktop coordinates added independently.

## Verification

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m bg3_helper.test_arena
```

The disposable arena's **Run bridge self-test** button exercises actual software capture, one mouse click, one key press, one scroll, and duplicate suppression. It writes before/after screenshots and `result.json` to `.runtime/self-test/`. No game/save is used. To connect a separate companion to it, use an isolated runtime:

```powershell
./.venv/Scripts/python.exe -m bg3_helper --runtime .runtime/test-panel panel --test-target
```

Tests use a fake desktop for negative monitor coordinates, frame invalidation, input policy, duplicate/uncertain results, and local HTTP behavior. Real game testing remains a separate acceptance step: capture the actual scene, inspect tooltip detail and colors, then try one harmless menu action.

Native implementation references: [MSS capture examples](https://python-mss.readthedocs.io/latest/examples.html), [Windows DPI awareness](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext), and [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput).
