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
    sub.add_parser("status", help="Read game, input, and latest capture state")
    sub.add_parser("capture", help="Capture the visible game window without switching focus")
    sub.add_parser("stop", help="Disable input immediately")
    sub.add_parser("doctor", help="Inspect local displays and BG3 windows; does not capture")
    note = sub.add_parser("note", help="Show this session's advice in the panel")
    note.add_argument("text")
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
    args = parser.parse_args()
    try:
        from .transport import request
        if args.command == "panel":
            from .panel import run_panel
            run_panel(args.runtime.resolve(), args.test_target)
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
            for name in ("x", "y", "button", "key", "steps"):
                value = getattr(args, name)
                if value is not None:
                    body[name] = value
            result = request(args.runtime, "action", body)
        elif args.command == "crop":
            result = request(args.runtime, "crop", {n: getattr(args, n) for n in ("x", "y", "width", "height")})
        elif args.command == "note":
            result = request(args.runtime, "note", {"text": args.text})
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
