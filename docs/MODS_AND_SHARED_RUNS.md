# Mods and shared-run preparation

Status: proposed feature; no local mod inventory was collected for this document. Updated 2026-09-05.

## First useful version

Add a **Mods & run summary** view with **Refresh**, a previous-scan comparison, and **Copy summary**. It should answer: "What is configured on my PC, what changed, and what do my friends need to know before our next run?"

The first version records local evidence and produces plain text. It does not download, install, update, disable, reorder, or redistribute mods; modify `modsettings.lsx`; load a save; contact friends; or automatically send inventory to Codex. There is no shared online database. A later version can compare two deliberately exchanged manifests.

Larian documents matching mod versions and an in-game verification flow when loading a modded save or joining multiplayer. The companion should supplement that flow with a readable record, not claim to replace it. [Larian's mod guide](https://baldursgate3.game/news/community-update-29-playing-with-mods_124)

## Sources and limits

Paths below are discovery candidates to validate against fixtures and the user's selected BG3 profile. They are not findings about the current machine.

| Source | What to record | What it does not prove |
| --- | --- | --- |
| `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\PlayerProfiles\<selected profile>\modsettings.lsx` | Saved configuration entries, UUIDs, names, exact raw version values, and order where the corresponding structures exist. Keep configured order distinct from metadata list order. | That the running game successfully loaded those entries, or that the file describes the explicitly linked save. |
| `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\*.pak` | File presence, filename, size, and modification time. Associate with a configured entry only when supported by reliable metadata. | That every file is enabled, that a filename is a mod UUID/version, or that all kinds of mods have been discovered. |
| An explicitly selected game installation | Readable executable version and narrowly identified extension markers. An extender loader candidate such as `bin\DWrite.dll` is a file observation. | That the DLL is definitely Script Extender, that it is loaded, or what extender version is active. |
| Manual notes | The player's chosen run label, host/player alias, explicit save reference, character/party note, objective, and known setup exceptions. | Automatically discovered game state or verified compatibility. |

BG3 Mod Manager documents the user Mods folder and exporting a profile's saved load order to `modsettings.lsx`. Its separate JSON/text exports may be an optional adapter later. Do not require BG3 Mod Manager or parse an undocumented export as though it were a stable interface. [Maintainer's README](https://github.com/LaughingLeader/BG3ModManager)

Norbyte's installation places its loader in the game's `bin` directory. Filename presence alone is weaker evidence than a verified runtime version. Do not execute a discovered DLL or installer to inspect it. [Script Extender installation instructions](https://github.com/Norbyte/bg3se/releases)

Read the selected profile explicitly; do not silently choose the newest profile. Reuse the existing configurable game-data root. Missing directories mean "source not found," while denied access or invalid XML means "source could not be read." Neither should become "no mods installed." Do not scan unrelated personal folders or recursively classify the game's base `.pak` files as mods.

Loose-file overrides, native plugins, manually installed files, manager-specific metadata, and live runtime state can be outside the first scan's coverage. Display that coverage on every report. Preserve unsupported entries as unknown rather than guessing their origin, enablement, version, or multiplayer requirements.

## Snapshot and change contract

Store versioned snapshots alongside the chosen play session, using existing history conventions. A snapshot contains:

- Schema version, snapshot ID, scan time, selected game profile, source read results, and any detected or manually supplied game version with its provenance.
- The companion play-session ID and explicit save-reference revision, if selected. Association is a user choice, not evidence that the mod configuration belongs to that save.
- Configured entries keyed by UUID when available, preserving raw versions as decimal strings so large version values cannot lose precision in another tool.
- Package-file observations as a separate collection. Do not merge an ambiguous filename into a UUID record.
- Per-entry evidence and explicit unknown fields. An entry is "configured enabled" or "file present," not "confirmed loaded" without separate live evidence.
- Optional run notes, their last edit time, and the fields the user chose to include in a shared summary.

Compare a new scan with the previous snapshot for the same selected profile. Report added/removed configured entries, changed known versions, and changed known order. Report file changes separately. If a source fails, do not manufacture removals from its missing results. If files change during inspection, label the snapshot incomplete and offer a fresh scan; do not silently mix conflicting reads into a compatibility verdict.

Run scans off the Tk event loop. Use bounded reads and safe XML parsing; record malformed, oversized, duplicate, and partially written data as diagnostics. Treat names and notes as untrusted text, including when later included in an agent request. Preserve existing snapshot versions or report unsupported versions without resetting personal data.

## Copyable report

The preview is the authoritative list of fields that will leave the app when copied. By default include the scan time, a user-selected run alias, game version if known, configured mod identifiers/versions/order, file-only observations, coverage limits, and changes since the previous scan. Exclude absolute paths, Windows usernames, account/conversation IDs, tokens, raw configuration, images, save filenames, and personal notes. Save labels and notes are optional fields with explicit inclusion controls.

Use an allowlist to construct the report rather than removing a few known secrets from a raw snapshot. Render names/notes as plain text; do not interpret their contents as commands or instructions. Do not copy automatically on refresh.

Illustrative output only; the entries below are invented:

```text
BG3 Companion - shared-run preparation
Run alias: Friday campaign
Observed at: 2026-09-05 18:00 UTC
Game version: unknown
Coverage: saved mod configuration + user Mods folder; running game not verified

Configured entries:
1. Example UI mod | UUID: <example UUID> | version: <exact stored value>
2. Example dice mod | UUID: <example UUID> | version: unknown

Files without a verified configuration match:
- example-package.pak | present; enablement unknown

Changes since previous scan: one configured version changed
Not checked: loose overrides, native plugin runtime, multiplayer compatibility
Save reference and personal notes: excluded
```

Offer a local detailed view containing source paths for diagnosis, clearly separate from the shared preview. Do not promise automatic redaction of arbitrary user-authored notes; users review any optional text before copying it.

## Shared-run notes

Keep a lightweight record of the campaign alias, optional host/player aliases, manually entered character/party notes, next objective, and an explicit save reference. This can reuse play-session metadata instead of introducing a separate collaboration service. A run note should say whether it was entered by the player or observed from a particular screenshot.

Keep personal resolution, accessibility preferences, and profile overrides separate from mod/game configuration. Different local graphics preferences are not, by themselves, evidence of a multiplayer mismatch. The first report provides material for a conversation; it does not coordinate sessions, change another PC, or enable game input for co-op.

## Acceptance criteria for the source beta

1. A fresh installation with no game profile opens the view and reports missing sources without crashing or claiming an empty verified mod list.
2. Fixtures cover multiple profiles, valid and malformed XML, absent optional fields, duplicate UUIDs, raw 64-bit versions, file-only packages, changed files during scanning, and unreadable sources.
3. Scanning does not write to game/mod/save directories. Fixture hashes remain unchanged; the only new data is companion-owned history.
4. Refresh remains responsive and cannot delay STOP. It requires neither INPUT nor a Codex connection, captures no screen, and submits no model request.
5. Snapshot history survives restart. Comparing two scans preserves order, separates unknowns, and avoids false removals after a read failure.
6. Copy summary exactly matches its preview and includes no private fields by default. Test with synthetic usernames, absolute paths, and token-like strings in local-only metadata.
7. Manual run notes and explicit save association persist; sharing them is optional. Selected settings overrides remain local unless deliberately included.
8. Two friends can exchange text summaries and identify a known mod-version or order difference. A report never declares "multiplayer compatible" merely because the available fields match.

## Later improvements

- Explicit import/export of a small, versioned, path-free JSON manifest and a two-report comparison. Match on stable IDs, preserve unknowns, and identify differences without proposing automatic fixes.
- Optional package hashes to disambiguate identical names or versions, with progress and cancellation for large files. Hash equality is still not a multiplayer guarantee.
- Adapters for confirmed BG3 Mod Manager exports and other supported metadata sources, based on fixtures and provenance.
- Better recognition of overrides and extension versions, plus manually recorded results from BG3's own verification flow.
- A reusable mod-audit skill if the deterministic inventory needs an agent-assisted explanation. It should consume the established report, not independently scan the machine.

Cross-platform and live multiplayer input support remain separate projects. Automatic mod synchronization, save synchronization, package distribution, and remote control are outside this beta.
