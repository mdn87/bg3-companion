---
name: bg3-smart-move
description: Carry out one bounded BG3 companion Smart next move request using current screenshots and verified gestures, with its result recorded in play history.
---

The button request supplies the project, runtime, and request ID. Claim that ID first. If it is cancelled, expired, replaced, or unavailable, stop. Do not create another request or revive its input permission.

Use the repository's `.venv/Scripts/python.exe -m bg3_helper --runtime RUNTIME` commands. The claimed request contains the user's objective, captured start frame, `allow_actions`, play-session/save context, and gesture limit. Read its context and relevant recent `history`; an explicit save link does not prove which save is loaded.

Capture a fresh frame and inspect `preview_path`. Use native crops for tooltips, but use the original preview's coordinate system for actions. Never reuse menu coordinates from a prior resolution, prior play session, or this skill's examples. Frame IDs are single-use and expire after 60 seconds.

If `allow_actions` is false, recommend one useful next step and send no input. If true, choose one small, useful move that fits the objective and the three-gesture budget. When the scene is ambiguous, return advice or the missing information instead of guessing. Do not make story choices, save/load, rest, or exit the game under this general next-move trigger.

Every `act` must include `--smart-request REQUEST_ID`, a fresh `--frame`, and a unique `--request-id` for that gesture. Inspect `after.preview_path` after each action: `input_sent` reports transport, not game success. Reuse the same gesture request ID only for an identical uncertain retry; never issue a replacement ID to replay an uncertain effect.

The bridge requires game focus. The button normally returns focus before queuing; if a later focus change blocks an otherwise authorized action, use the available Windows window tool to activate the identified BG3 window, then capture again. Respect the actual INPUT state. Do not operate the INPUT switch to bypass a timeout or STOP.

Finish with `finish REQUEST_ID --text "..."`, describing what the after image confirms and any remaining uncertainty. Captures, gestures, and the result are retained automatically in that play session. Do not continue playing after finishing. See the [command reference](../../../README.md) for syntax.
