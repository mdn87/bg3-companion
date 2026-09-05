---
name: bg3-system-setup
description: Audit or apply a saved BG3 companion setup profile, recording current menu settings, overrides, and before/after evidence for repeatable development and play setup.
---

Use the existing companion with the repository's `.venv/Scripts/python.exe -m bg3_helper --runtime RUNTIME`. A Smart system setup request must be claimed first. Stop if it is cancelled, expired, replaced, or unavailable. [CLI reference](../../../README.md).

Use the frozen `setup.profile` in the claimed request, including its revision and override note. Balanced is the companion development baseline. All three supplied profiles are starting points, not benchmarks. If a direct request does not supply a profile, read `profiles` and honor the user's active choice.

The request saves a graphics/system baseline and starting screenshot automatically. Capture again before deciding. Inspect the actual menu and record the visible values with `settings-observe --frame FRAME_ID --values JSON --note "Before setup"`. Source config can lag the live menu. Keep configured game resolution, client/capture dimensions, display dimensions, and measured performance separate.

With input off or `allow_actions` false, audit and recommend only. With input permitted, navigate to game settings and apply only differences requested by the profile, within its twelve-gesture budget:

- `borderless: true` requests Borderless Window; false leaves the existing display mode alone.
- `background_audio` maps to the inverse of **Mute Sound When Inactive**.
- `unlock_mouse` maps to the inverse of **Lock Mouse to Window**.
- `resolution: Keep current` preserves the configured game resolution. `Match display` uses the monitor containing the game, if the game menu offers that resolution. Explicit dimensions refer to the game setting, not Windows display settings.
- `upscaling: Keep current` leaves it alone. DLSS Quality requires the corresponding upscaling type and Quality mode. DLAA requires a visible compatible option; do not infer enum meanings from the config file.
- `target_fps` is the desired in-game frame cap, when a cap control is visibly available. It is not measured FPS and does not promise the system can maintain it. Do not guess a missing control.

Record before values so the user can return to them. Re-observe after every gesture and after any resolution change; preview coordinates and target identity can change. Include `--smart-request REQUEST_ID` on every `act`. Use the Windows window tool to focus the identified game when needed, but do not enable input to bypass STOP or its timer. Never change drivers, OS display configuration, mods, game saves, or gamma/HDR calibration as part of this setup button.

Record the verified after-values using `settings-observe`, with the profile name/revision in the note. A final `settings-snapshot` retains another copy of the saved graphics config; it can still lag live changes. Do not restore a config file over a running game. If the gesture budget runs out, report the verified changes and remaining settings rather than claiming the entire profile was applied.

Finish through `finish REQUEST_ID --text "..."`. State what changed, what was already correct, and what was not measured. Do not claim optimization gains without an actual measurement, infer active saves from timestamps, or launch further requests automatically.
