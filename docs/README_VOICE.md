# Public README voice

## Reader and purpose

Write for a friend who plays Baldur's Gate 3 and is curious about this project. Assume familiarity with the game, not with Python, agent systems, or release engineering. The reader should understand what the companion does, what using it feels like, and how far along it is before reaching a development link.

## Voice

Use a document-facing Dean / plain-English voice: casual and competent, point first, concrete subjects and verbs, natural contractions, and short paragraphs. Explain Codex's role when it first appears. Keep real button names intact. Use a list only when the reader is choosing between controls or comparing actual things.

Drop corporate filler, unexplained project shorthand, artificial enthusiasm, clever analogies, and closing summaries. Don't use em dashes. Keep the limitations that affect a player's decision; don't bury them behind a cheerful description.

This guide applies to public prose. It doesn't change command syntax, schemas, task authority, application behavior, or permission rules.

## Facts a rewrite must preserve

- The app is an experimental Windows companion. Live input targets single-player. There is a local prototype, not a tested install-and-play release for friends.
- Explain screen gives advice without input. Capture only saves locally without a model request. Smart next move can use at most three gestures only when INPUT was enabled for that request, inspecting the screen after each.
- INPUT starts off. Permission lasts ten minutes. Enabling it alone starts no work. STOP cancels the request and disables input, but cannot retract input already accepted. Advice-only requests cannot acquire input later.
- Work is button-triggered, not continuous play. A busy Codex conversation can delay the result. AI instructions are not proof that an action is safe or correct.
- History, explicit save references, and three editable settings profiles already exist. A save reference is not proof of the loaded save. Profiles are preferences, not measured performance presets.
- Smart system setup currently allows up to twelve settings gestures with INPUT on. Full live profile application remains unverified. Advice-only setup regardless of INPUT is a proposal, not current behavior.
- Local capture and history are distinct from AI analysis. Requested screenshot previews and relevant context go to the linked Codex conversation. The project uses that conversation's model/account limits, without a separate model API key or required BG3 mod.
- Mod inventory, scan differences, manually entered run/party notes, and previewed copyable reports are proposed features. They do not imply mod installation, synchronization, compatibility guarantees, multiplayer input, or an AI party member.
- Preserve the scope and date of test evidence. A direct menu capture/click is not a complete button workflow or gameplay test. Publication does not complete release acceptance.

## Editing procedure

Before rewriting, pin the source revision and record its claims and qualifiers. Draft the prose, remove filler, then compare every claim back to the source. Check especially for changes from permitted to safe, implemented to tested, planned to available, or local to offline.

Keep the exact technical material in the reference rather than compressing away requirements. Check relative links and the `#verification` anchor. Report whether review was a self-check or an independent review; don't claim a separate reviewer ran when none did.

## Initial split

The source README at commit `47ba1e4e039099290523db958d8dbd73dbce57ec` is retained byte-for-byte as `TECHNICAL.md` in this documentation change. Its original blob is `1352ae641944337a0c90fd0802bd42a766a2c92c`. The new README is an audience-specific overview, not a replacement technical specification.

The draft implementation plan was read at `b61b212456fdbce4bae65a8a1f2c69750c577632`. All six work items were unstarted at that inspection. Refresh status from source when editing, rather than treating these historical references as current forever.
