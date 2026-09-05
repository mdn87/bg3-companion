# BG3 Companion

**An experimental AI sidekick for Baldur's Gate 3 on Windows.**

Ask about what's on your screen, get a suggestion for your next move, and keep a record of your playthrough. You decide whether the assistant can click or press keys in the game.

The companion sits beside BG3, usually on a second monitor. When you ask for help, it takes a screenshot and sends it to your linked Codex conversation. Codex supplies the AI; the companion gives it a view of the game and puts the reply back in the panel.

There's a working prototype, with limited testing on one development PC. **It isn't an install-and-play release for friends yet.** You can follow the project here without needing to set anything up.

## What using it looks like

Keep the game visible, optionally type what you're trying to do, and choose a button:

- **Explain screen** asks for an explanation of the current screen. It gives advice without controlling the game.
- **Smart next move** asks for a useful next step. With **INPUT** off, it gives advice. With INPUT enabled before you submit the request, it can try up to three mouse or keyboard actions, checking the screen after each. When the next step is uncertain, it's instructed to give advice instead.
- **Capture only** saves a screenshot locally without asking the AI anything.

**Session & save** and **History** keep screenshots, questions, replies, and settings observations together under a named play session. You can attach a save reference to help remember where you left off. That reference doesn't tell the companion which save is actually loaded, and it doesn't load or change your saves.

## You control the input

INPUT starts off. Turning it on grants permission for 10 minutes but doesn't start a move by itself. **STOP** cancels the current request and turns input off. It prevents further actions; it can't undo a click or key press Windows has already accepted.

A request sent for advice can't gain control just because you turn INPUT on later. The assistant runs when you ask it to, rather than continuously playing in the background. Replies can take time, especially when the linked Codex conversation is busy.

Live input is intended for single-player. The AI can misread a screen or give bad advice, and instructions to avoid story choices aren't a guarantee that it will never make a mistake. Full gameplay and complete button-to-game workflows still need testing.

## Settings help

The prototype can record current settings and keep three editable preference profiles: **Balanced**, **Higher frame rate**, and **Image quality**. They're starting preferences, not promises of better performance.

**Smart system setup** asks the AI to review the selected profile. With INPUT off it gives advice; with INPUT on, the current code permits up to 12 settings actions. Applying a whole profile hasn't been fully verified. The next development plan proposes keeping this feature advice-only until that work is tested.

## Playing with friends later

A planned addition would list your installed mods and configuration, show what changed since the last scan, and let you copy a summary with optional campaign or party notes. That should make it easier to compare setups before a shared run.

**Those features aren't built yet.** The plan is read-only inspection and a report you choose to share. It won't install or sync mods, guarantee compatibility, or turn the AI into another player in your party.

## What it needs and where your data goes

The current prototype needs Windows, a visible BG3 window, and a working connection to an existing Codex conversation. It uses that conversation's model and account limits. No BG3 mod, capture hardware, or separate model API key is required.

Screenshots and play history are stored locally. **Asking for AI help also sends a screenshot preview and relevant context to Codex for analysis.** The app running on your PC doesn't make the AI part offline. Keep personal information out of screenshots or notes you send.

Installation instructions and testing on other PCs are still ahead. The [technical reference](TECHNICAL.md) covers the existing development setup, controls, commands, and limitations.

## Verification

The [development record](TECHNICAL.md#verification) reports 70 automated tests and a limited live BG3 menu capture-and-click check on September 5, 2026. That check used direct commands, not a complete Smart next move button request. It doesn't establish a tested friend release.

For a closer look, read the [product concept](docs/CONCEPT.md) or the [draft plan for the next improvements](https://github.com/mdn87/bg3-companion/pull/1). The plan covers clearer connection errors, a more usable panel, history recovery, and the proposed mod/run summaries. Its six implementation tasks haven't started.
