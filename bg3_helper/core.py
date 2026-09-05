"""Frame state, coordinate mapping, and bounded gesture validation."""
from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from .shortcuts import INPUT_SHORTCUT


class BridgeError(Exception):
    pass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class Window:
    hwnd: int
    pid: int
    executable: str
    title: str
    rect: Rect


GAME_KEYS = {
    **{str(i): ord(str(i)) for i in range(10)},
    **{c: ord(c.upper()) for c in "wasdqeiomkzxcvgbnrtuyhjl"},
    "escape": 0x1B, "tab": 0x09, "space": 0x20, "enter": 0x0D,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
}


def pixel_point(x, y, image_size, rect):
    """Map actual preview pixels to physical desktop coordinates, including negatives."""
    iw, ih = image_size
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (x, y)):
        raise BridgeError("Coordinates must be finite numbers.")
    if not (0 <= x < iw and 0 <= y < ih):
        raise BridgeError(f"Point must be inside the {iw} x {ih} preview.")
    return (rect.left + min(rect.width - 1, int(x * rect.width / iw)),
            rect.top + min(rect.height - 1, int(y * rect.height / ih)))


def visual_difference(a, b):
    size = (96, 54)
    a = a.convert("RGB").resize(size)
    b = b.convert("RGB").resize(size)
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


class Bridge:
    def __init__(self, desktop, output: Path, *, clock=time.monotonic):
        self.desktop = desktop
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.lock = threading.RLock()
        self.control_lock = threading.Lock()
        self.stopped = threading.Event()
        self.stop_revision = 0
        self.armed_until = 0.0
        self.frame = None
        self.frame_pixels = None
        self.frame_time = 0.0
        self.used = True
        self.results = {}
        self.note = "Open BG3, then press Explain screen or Smart next move. Your result will appear here."
        self.last_error = ""
        self.session = None

    @property
    def armed(self):
        return not self.stopped.is_set() and self.clock() < self.armed_until

    def arm(self, expected_stop_revision=None):
        with self.lock:
            revision = self.stop_revision if expected_stop_revision is None else expected_stop_revision
            self.desktop.target()  # Must have exactly one eligible live target.
            with self.control_lock:
                if revision != self.stop_revision:
                    raise BridgeError("Input was stopped while the enable request was waiting.")
                self.stopped.clear()
                self.armed_until = self.clock() + 600
                self.last_error = ""

    def stop(self):
        # Deliberately does not wait for the capture/action lock.
        with self.control_lock:
            self.stopped.set()
            self.stop_revision += 1
            self.armed_until = 0

    def status(self):
        with self.lock:
            try:
                target = asdict(self.desktop.target())
                target_error = None
            except BridgeError as exc:
                target, target_error = None, str(exc)
            return {"target": target, "target_error": target_error,
                    "input_enabled": self.armed,
                    "input_seconds_remaining": max(0, int(self.armed_until - self.clock())) if self.armed else 0,
                    "latest": self.frame, "note": self.note, "last_error": self.last_error,
                    "session": self.session.status() if self.session else None}

    def _capture(self):
        target = self.desktop.target()
        before = self.clock()
        pixels = self.desktop.capture(target)
        if self.desktop.target() != target:
            raise BridgeError("Game window changed during capture. Capture again.")
        if pixels.size != (target.rect.width, target.rect.height):
            raise BridgeError("Capture dimensions do not match the game window.")
        frame_id = uuid.uuid4().hex
        full = self.output / f"{frame_id}.png"
        preview_path = self.output / f"{frame_id}.preview.png"
        preview = pixels.copy()
        preview.thumbnail((1600, 1000), Image.Resampling.LANCZOS)
        pixels.save(full)
        preview.save(preview_path)
        frame = {
            "frame_id": frame_id, "captured_at": datetime.now(timezone.utc).isoformat(),
            "window": asdict(target), "full_path": str(full), "preview_path": str(preview_path),
            "image_width": preview.width, "image_height": preview.height,
            "capture_ms": round((self.clock() - before) * 1000),
            "coordinates": "Use pixels in preview_path for actions; full_path is for detail.",
            "capture_backend": "mss-visible-window-region",
        }
        (self.output / f"{frame_id}.json").write_text(json.dumps(frame, indent=2), encoding="utf-8")
        self.frame, self.frame_pixels, self.frame_time = frame, pixels, before
        self.used = False
        return frame

    def capture(self):
        with self.lock:
            return self._capture()

    def crop(self, x, y, width, height):
        """Read a native-resolution crop of the latest saved frame; never changes action space."""
        with self.lock:
            if self.frame is None:
                raise BridgeError("Capture first.")
            values = (x, y, width, height)
            if any(type(v) is not int for v in values) or min(x, y) < 0 or min(width, height) <= 0:
                raise BridgeError("Crop must use non-negative integer coordinates and positive dimensions.")
            if x + width > self.frame_pixels.width or y + height > self.frame_pixels.height:
                raise BridgeError("Crop must fit inside the full-resolution image.")
            path = self.output / f"{self.frame['frame_id']}.crop-{uuid.uuid4().hex[:8]}.png"
            self.frame_pixels.crop((x, y, x + width, y + height)).save(path)
            return {"path": str(path), "frame_id": self.frame["frame_id"],
                    "native_crop": [x, y, width, height],
                    "coordinates": "Crop pixels cannot be submitted as action coordinates. Use the preview."}

    def act(self, request):
        with self.lock:
            if not isinstance(request, dict):
                raise BridgeError("Action must be a JSON object.")
            request_id = request.get("request_id")
            if not isinstance(request_id, str) or not 1 <= len(request_id) <= 80:
                raise BridgeError("Provide a request_id of 1–80 characters.")
            if request_id in self.results:
                previous, result = self.results[request_id]
                if request != previous:
                    raise BridgeError("request_id was already used for a different action.")
                return result
            if not self.armed:
                raise BridgeError(f"Input is off. Turn the INPUT switch on in the companion or use {INPUT_SHORTCUT}.")
            if self.frame is None or request.get("frame_id") != self.frame["frame_id"]:
                raise BridgeError("Action must reference the latest frame_id.")
            if self.used or self.clock() - self.frame_time > 60:
                raise BridgeError("Frame is used or older than 60 seconds. Capture again.")
            target = self.desktop.target()
            if asdict(target) != self.frame["window"]:
                raise BridgeError("Game window moved, resized, or changed. Capture again.")
            if not self.desktop.foreground(target):
                raise BridgeError("Return focus to the game before requesting an action.")
            kind = request.get("kind")
            action = {"kind": kind}
            if kind in {"move", "click", "scroll"}:
                action["point"] = pixel_point(request.get("x"), request.get("y"),
                    (self.frame["image_width"], self.frame["image_height"]), target.rect)
                if kind == "click":
                    button = request.get("button", "left")
                    if button not in {"left", "right", "middle"}:
                        raise BridgeError("Button must be left, right, or middle.")
                    action["button"] = button
                if kind == "scroll":
                    steps = request.get("steps")
                    if type(steps) is not int or not 1 <= abs(steps) <= 5:
                        raise BridgeError("Scroll steps must be a nonzero integer between -5 and 5.")
                    action["steps"] = steps
            elif kind == "key":
                key = request.get("key")
                if key not in GAME_KEYS:
                    raise BridgeError("Unsupported key. Use one documented game key; chords are disabled.")
                action["vk"] = GAME_KEYS[key]
            else:
                raise BridgeError("Action kind must be move, click, scroll, or key.")
            # Re-observe just before sending input; animation can cause conservative rejection.
            current = self.desktop.capture(target)
            delta = visual_difference(self.frame_pixels, current)
            if delta > 18:
                raise BridgeError(f"The visible scene changed (difference {delta:.1f}). Capture again.")
            if self.stopped.is_set() or not self.armed:
                raise BridgeError("Input was stopped.")
            if self.session:
                self.session.before_action(request)
            elif request.get("smart_request_id"):
                raise BridgeError("This companion has no active session request.")
            self.used = True
            result = {"request_id": request_id, "status": "outcome_unknown"}
            # Reserve before the first OS event. An uncertain result must never be replayed.
            self.results[request_id] = (dict(request), result)
            try:
                self.desktop.send(target, action, self.stopped)
                time.sleep(0.2)
                after = self._capture()
                result = {"request_id": request_id, "status": "input_sent", "after": after,
                          "message": "Inspect the after frame to verify the intended game effect."}
            except Exception as exc:
                self.stop()
                result = {"request_id": request_id, "status": "outcome_unknown", "error": str(exc),
                          "message": "Input disabled. Capture and inspect before any new action."}
            self.results[request_id] = (dict(request), result)
            with (self.output / "actions.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps({"request": request, "result": result}) + "\n")
            return result
