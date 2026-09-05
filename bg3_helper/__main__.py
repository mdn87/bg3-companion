import argparse
import json
from pathlib import Path
import sys
import uuid

from .core import BridgeError


def main():
    parser = argparse.ArgumentParser(description="BG3 local capture/control bridge for an active agent session")
    parser.add_argument("--runtime", type=Path, default=Path(__file__).resolve().parent.parent / ".runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    panel = sub.add_parser("panel", help="Open the native companion and local bridge")
    panel.add_argument("--test-target", action="store_true", help="Use only the disposable test arena")
    panel.add_argument("--data", type=Path, help="Play-session storage; defaults to play-sessions beside the normal runtime")
    sub.add_parser("status", help="Read game, input, and latest capture state")
    sub.add_parser("capture", help="Capture the visible game window without switching focus")
    sub.add_parser("stop", help="Disable input immediately")
    sub.add_parser("doctor", help="Inspect local displays and BG3 windows; does not capture")
    connect = sub.add_parser("connect", help="Link companion buttons to an existing Codex conversation")
    connect.add_argument("thread_id")
    smart = sub.add_parser("request", help="Submit one companion request to the linked conversation")
    smart.add_argument("kind", choices=["explain", "smart", "setup", "connection_test"])
    smart.add_argument("--objective", default="")
    claim = sub.add_parser("claim", help="Check and claim a queued companion request")
    claim.add_argument("request_id")
    finish = sub.add_parser("finish", help="Return the result to the companion and finish the request")
    finish.add_argument("request_id")
    finish.add_argument("--text", required=True)
    note = sub.add_parser("note", help="Show this session's advice in the panel")
    note.add_argument("text")
    history = sub.add_parser("history", help="List play sessions and their capture/request/settings events")
    history.add_argument("--session-id")
    history.add_argument("--limit", type=int, default=100)
    sub.add_parser("saves", help="Discover local save names; does not guess which save is loaded")
    play = sub.add_parser("play", help="Name, resume, or associate a play session")
    play.add_argument("operation", choices=["new", "resume", "rename", "link"])
    play.add_argument("--label")
    play.add_argument("--session-id")
    play.add_argument("--save-id")
    play.add_argument("--name", default="")
    play.add_argument("--note", default="")
    profiles = sub.add_parser("profiles", help="Read or save setup profile overrides")
    profiles.add_argument("--profile-id", choices=["balanced", "performance", "quality"])
    profiles.add_argument("--overrides", type=json.loads, help="JSON object of setup preferences")
    profiles.add_argument("--note", default="")
    sub.add_parser("settings", help="Read tracked settings and profiles")
    sub.add_parser("settings-snapshot", help="Save a read-only system and graphics-config baseline")
    observe = sub.add_parser("settings-observe", help="Record menu settings read from a saved frame")
    observe.add_argument("--frame", required=True)
    observe.add_argument("--values", type=json.loads, required=True)
    observe.add_argument("--note", default="")
    crop = sub.add_parser("crop", help="Crop the latest full-resolution frame for inspection")
    for name in ("x", "y", "width", "height"):
        crop.add_argument(name, type=int)
    action = sub.add_parser("act", help="Perform one action against a fresh frame, then capture")
    action.add_argument("kind", choices=["move", "click", "key", "scroll"])
    action.add_argument("--frame", required=True)
    action.add_argument("--request-id", default=None, help="Reuse the exact ID only when retrying an uncertain request")
    action.add_argument("--x", type=float)
    action.add_argument("--y", type=float)
    action.add_argument("--button", choices=["left", "right", "middle"], default="left")
    action.add_argument("--key")
    action.add_argument("--steps", type=int)
    action.add_argument("--smart-request", dest="smart_request_id", help="Companion request authorizing this gesture")
    args = parser.parse_args()
    try:
        from .transport import request
        if args.command == "panel":
            from .panel import run_panel
            run_panel(args.runtime.resolve(), args.test_target, data=args.data)
            return
        if args.command == "doctor":
            from dataclasses import asdict
            from .windows import WindowsDesktop
            desktop = WindowsDesktop()
            import mss
            with mss.mss() as grabber:
                monitors = grabber.monitors[1:]
            result = {"platform": sys.platform, "monitors": monitors,
                      "game_windows": [asdict(w) for w in desktop.windows()],
                      "backend": "mss-visible-window-region", "requires_kvm": False}
        elif args.command == "act":
            body = {"request_id": args.request_id or uuid.uuid4().hex, "frame_id": args.frame,
                    "kind": args.kind}
            for name in ("x", "y", "button", "key", "steps", "smart_request_id"):
                value = getattr(args, name)
                if value is not None:
                    body[name] = value
            result = request(args.runtime, "action", body)
        elif args.command == "crop":
            result = request(args.runtime, "crop", {n: getattr(args, n) for n in ("x", "y", "width", "height")})
        elif args.command == "note":
            result = request(args.runtime, "note", {"text": args.text})
        elif args.command == "connect":
            result = request(args.runtime, "connect", {"thread_id": args.thread_id})
        elif args.command == "request":
            result = request(args.runtime, "request", {"kind": args.kind, "objective": args.objective})
        elif args.command == "claim":
            result = request(args.runtime, "claim", {"request_id": args.request_id})
        elif args.command == "finish":
            result = request(args.runtime, "finish", {"request_id": args.request_id, "text": args.text})
        elif args.command == "history":
            result = request(args.runtime, "history", {"session_id": args.session_id, "limit": args.limit})
        elif args.command == "play":
            result = request(args.runtime, "play", {key: getattr(args, key) for key in
                             ("operation", "label", "session_id", "save_id", "name", "note") if getattr(args, key) is not None})
        elif args.command == "profiles":
            result = request(args.runtime, "profiles", {key: getattr(args, key) for key in
                             ("profile_id", "overrides", "note") if getattr(args, key) is not None})
        elif args.command == "settings-observe":
            result = request(args.runtime, "settings-observe", {"frame_id": args.frame, "values": args.values, "note": args.note})
        else:
            result = request(args.runtime, args.command)
        print(json.dumps(result, indent=2))
        if result.get("status") == "outcome_unknown":
            sys.exit(3)
    except BridgeError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
