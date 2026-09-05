# Contributing to BG3 Companion

## Start here

Read `TECHNICAL.md` for the existing controls, command interface, input restrictions, architecture, and verification record. Read the relevant application source before changing behavior. `docs/CONCEPT.md`, `docs/SOURCE_BETA_PLAN.md`, and `docs/MODS_AND_SHARED_RUNS.md` distinguish product direction from implemented features.

The next implementation milestone is local work on the existing development setup. Installation redesign, fresh installations, testing on other devices, packaging, hosted CI, retention automation, and synchronization remain deferred. Draft PR #1 carries the local plan and its task manifest. Read its current state before using it; a proposed task is not permission to run the app, inspect personal data, or start implementation.

## Keep the public entry point readable

`README.md` is for curious friends and players who may not develop software. Explain the experience, current limits, and next useful improvements in ordinary language. Use `docs/README_VOICE.md` when editing it. Keep command inventories and architecture in `TECHNICAL.md`, and implementation contracts in the appropriate development documents.

Do not put machine nicknames, user-specific absolute paths, unrelated infrastructure, or agent-routing terminology into the public introduction. Technical documents are still public; moving information out of the README does not make it private.

## Preserve the distinctions

Keep current behavior, proposed changes, and verified behavior separate. In particular, Smart next move permits at most three gestures for a request submitted with INPUT enabled. Smart system setup currently permits up to twelve settings gestures when INPUT is on; making setup advice-only is a proposed code change, not something a documentation edit implements.

Preserve startup INPUT OFF, explicit time-limited permission, cancellation and expiry, frame/target validation, and action limits. Do not describe instructions to the AI as guarantees enforced by game-state detection. A selected save reference is not proof of the loaded save.

Explain that local capture/history does not mean offline AI: requested screenshots and relevant context go to the linked Codex conversation. Never commit runtime descriptors, credentials, screenshots, personal play history, or real saves.

Do not relabel an old test result as a new check. State exactly what was run and what remains unverified. Keep the README's `#verification` anchor working because development documents link to it.
