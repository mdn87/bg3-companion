"""Read-only system baselines and editable, unbenchmarked game setup profiles."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from .core import BridgeError
from .history import read_json, text_field, utc_now, write_json


PROFILE_DEFAULTS = {
    "balanced": {"label": "Balanced", "description": "Companion-friendly baseline; measure frame rate before tuning further.",
                 "target_fps": 60, "resolution": "Keep current", "upscaling": "Keep current"},
    "performance": {"label": "Higher frame rate", "description": "Starting point for responsiveness; the target is not a measured result.",
                    "target_fps": 120, "resolution": "Keep current", "upscaling": "DLSS Quality"},
    "quality": {"label": "Image quality", "description": "Starting point for image quality; may need a lower target after measurement.",
                "target_fps": 60, "resolution": "Match display", "upscaling": "DLAA"},
}
for _profile in PROFILE_DEFAULTS.values():
    _profile.update(borderless=True, background_audio=True, unlock_mouse=True)

RESOLUTIONS = ("Keep current", "Match display", "1920 x 1080", "2560 x 1440", "3840 x 2160")
UPSCALING = ("Keep current", "DLSS Quality", "DLAA")


class SettingsTracker:
    def __init__(self, history, *, inspect_system=None):
        self.history = history
        self.inspect_system = inspect_system or (lambda: {})
        self.path = history.root / "profiles.json"
        if not self.path.exists():
            write_json(self.path, {"version": 1, "active": "balanced", "profiles": {
                key: {"overrides": {}, "revision": 0, "note": ""} for key in PROFILE_DEFAULTS}})

    def profiles(self):
        with self.history.lock:
            bank = read_json(self.path)
            resolved = {}
            for key, defaults in PROFILE_DEFAULTS.items():
                entry = bank["profiles"][key]
                resolved[key] = {"profile_id": key, **defaults, **entry["overrides"],
                                 "revision": entry["revision"], "overrides": entry["overrides"],
                                 "note": entry["note"], "stage": "starter_not_benchmarked"}
            return {"active": bank["active"], "profiles": resolved}

    def select_profile(self, profile_id, overrides=None, note=""):
        if profile_id not in PROFILE_DEFAULTS:
            raise BridgeError("Choose Balanced, Higher frame rate, or Image quality.")
        note = text_field(note, "Override note", 500, allow_empty=True)
        if overrides is not None:
            if not isinstance(overrides, dict) or set(overrides) - {
                    "target_fps", "resolution", "upscaling", "borderless", "background_audio", "unlock_mouse"}:
                raise BridgeError("Profile contains an unsupported override.")
            for key, value in overrides.items():
                if key == "target_fps" and (type(value) is not int or not 30 <= value <= 240):
                    raise BridgeError("Target frame rate must be a whole number from 30 to 240.")
                if key == "resolution" and value not in RESOLUTIONS:
                    raise BridgeError("Choose a supported resolution preference.")
                if key == "upscaling" and value not in UPSCALING:
                    raise BridgeError("Choose a supported upscaling preference.")
                if key in {"borderless", "background_audio", "unlock_mouse"} and type(value) is not bool:
                    raise BridgeError("Comfort settings must be true or false.")
        with self.history.lock:
            bank = read_json(self.path)
            before = deepcopy(bank)
            bank["active"] = profile_id
            if overrides is not None:
                entry = bank["profiles"][profile_id]
                entry["overrides"] = {k: v for k, v in overrides.items() if v != PROFILE_DEFAULTS[profile_id][k]}
                entry["revision"] += 1
                entry["note"] = note
            write_json(self.path, bank)
            self.history.record("profile_updated", {"before": before, "after": bank, "note": note})
            return self.profiles()

    def snapshot(self, target=None, frame_id=None, request_id=None):
        with self.history.lock:
            snapshot_id = uuid.uuid4().hex
            directory = self.history.directory() / "settings" / snapshot_id
            directory.mkdir(parents=True)
            raw, sources, warnings = {}, [], []
            graphics = self.history.game_data / "graphicSettings.lsx"
            if graphics.exists():
                try:
                    if graphics.stat().st_size > 1_000_000:
                        raise ValueError("Graphics settings file is unexpectedly large.")
                    content = graphics.read_bytes()
                    tree = ET.fromstring(content)
                    for node in tree.iter("node"):
                        if node.get("id") == "ConfigEntry":
                            attributes = {a.get("id"): a.get("value") for a in node.findall("attribute")}
                            if attributes.get("MapKey"):
                                raw[attributes["MapKey"]] = attributes.get("Value")
                    backup = directory / "graphicSettings.lsx"
                    backup.write_bytes(content)
                    sources.append({"path": str(graphics), "snapshot_path": str(backup),
                                    "sha256": hashlib.sha256(content).hexdigest(), "kind": "saved_graphics_config"})
                except (OSError, ValueError, ET.ParseError) as exc:
                    warnings.append(f"Could not read graphics settings: {exc}")
            else:
                warnings.append("BG3 graphics settings were not found at the configured data location.")
            try:
                system = self.inspect_system()
            except Exception as exc:
                system = {}
                warnings.append(f"System inspection failed: {exc}")
            width, height = raw.get("ScreenWidth"), raw.get("ScreenHeight")
            configured_resolution = f"{width} x {height}" if width and height else None
            bank = self.profiles()
            value = {**self.history.context(), "snapshot_id": snapshot_id, "settings_snapshot_id": snapshot_id,
                     "captured_at": utc_now(), "request_id": request_id,
                     "frame_id": frame_id, "target": target, "system": system,
                     "configured_resolution": configured_resolution, "graphics_raw": raw,
                     "profile": bank["profiles"][bank["active"]], "sources": sources,
                     "warnings": warnings, "observations": self.observations(),
                     "performance": {"measured": False, "fps": None},
                     "note": "Saved configuration can lag the live menu. Window size is separate from configured rendering resolution."}
            write_json(directory / "snapshot.json", value)
            self.history.current["settings_snapshot_id"] = snapshot_id
            self.history._save()
            self.history.record("settings_snapshot", value)
            return value

    def observations(self):
        path = self.history.directory() / "settings" / "observations.json"
        return read_json(path) if path.exists() else {}

    def observe(self, frame_id, values, note=""):
        import re
        if not isinstance(frame_id, str) or not re.fullmatch(r"[a-f0-9]{32}", frame_id):
            raise BridgeError("Use a frame ID from this play session.")
        if not isinstance(values, dict) or not 1 <= len(values) <= 40:
            raise BridgeError("Record between 1 and 40 observed settings.")
        note = text_field(note, "Observation note", 500, allow_empty=True)
        for key, value in values.items():
            text_field(key, "Setting name", 100)
            if not isinstance(value, (str, int, float, bool)) or (isinstance(value, str) and len(value) > 200):
                raise BridgeError("Setting values must be short text, numbers, or booleans.")
            if isinstance(value, float) and not math.isfinite(value):
                raise BridgeError("Setting values must be finite.")
        with self.history.lock:
            frame_path = self.history.directory() / "captures" / (frame_id + ".json")
            if not frame_path.exists():
                raise BridgeError("The observation frame does not belong to this play session.")
            frame = read_json(frame_path)
            previous = self.observations()
            current = deepcopy(previous)
            changes = {}
            for key, value in values.items():
                before = previous.get(key, {}).get("value")
                current[key] = {"value": value, "frame_id": frame_id, "observed_at": utc_now(),
                                "captured_at": frame["captured_at"], "request_id": frame.get("request_id"),
                                "source": "agent_read_screen", "note": note}
                if key not in previous or before != value:
                    changes[key] = {"before": before, "after": value}
            write_json(self.history.directory() / "settings" / "observations.json", current)
            record = {"frame_id": frame_id, "values": values, "changes": changes, "note": note,
                      "request_id": frame.get("request_id"), "settings_snapshot_id": frame.get("settings_snapshot_id"),
                      "preview_path": frame["preview_path"]}
            self.history.record("settings_observed", record)
            return record

    def current(self):
        with self.history.lock:
            snapshot_id = self.history.current.get("settings_snapshot_id")
            snapshot = read_json(self.history.directory() / "settings" / snapshot_id / "snapshot.json") if snapshot_id else None
            return {"profiles": self.profiles(), "latest_snapshot": snapshot, "observations": self.observations()}
