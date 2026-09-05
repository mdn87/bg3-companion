"""Durable play sessions, save associations, and an append-only event history."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import threading
import uuid

from .core import BridgeError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text_field(value, name, maximum=160, allow_empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise BridgeError(f"{name} must contain {'0' if allow_empty else '1'}–{maximum} characters.")
    return value.strip()


def discover_saves(game_data):
    """Read names and file metadata only. A recent save is not proof it is loaded."""
    root = Path(game_data).resolve()
    profiles = root / "PlayerProfiles"
    saves = []
    if not profiles.is_dir():
        return saves
    for profile in profiles.iterdir():
        story = profile / "Savegames" / "Story"
        if not story.is_dir() or not story.resolve().is_relative_to(root):
            continue
        for pattern in ("*.lsv", "*/*.lsv"):
            for path in story.glob(pattern):
                try:
                    resolved = path.resolve()
                    if not resolved.is_relative_to(root):
                        continue
                    stat = resolved.stat()
                    relative = path.relative_to(root).as_posix()
                    saves.append({
                        "save_id": hashlib.sha256(relative.casefold().encode()).hexdigest()[:24],
                        "name": path.stem, "profile": profile.name, "relative_path": relative,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "size": stat.st_size,
                        "revision": hashlib.sha256(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}".encode()).hexdigest()[:24],
                        "association": "selected_file_metadata",
                    })
                except OSError:
                    continue  # A save may be replaced while the game is writing it.
    return sorted(saves, key=lambda item: item["modified_at"], reverse=True)


class PlayHistory:
    def __init__(self, root, game_data):
        self.root = Path(root).resolve()
        self.game_data = Path(game_data).resolve()
        self.lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)
        self.current = None
        pointer = self.root / "active.json"
        if pointer.exists():
            # A corrupt pointer is reported, not silently replaced with a new history.
            self.resume(read_json(pointer)["play_session_id"])
        else:
            self.new("BG3 · " + datetime.now().strftime("%Y-%m-%d"))

    def directory(self, session_id=None):
        session_id = session_id or self.current["play_session_id"]
        if not isinstance(session_id, str) or not re.fullmatch(r"\d{8}-\d{6}-[a-f0-9]{8}", session_id):
            raise BridgeError("Invalid play session ID.")
        path = self.root / session_id
        if not path.resolve().is_relative_to(self.root):
            raise BridgeError("Play session directory is outside the history folder.")
        return path

    def _save(self):
        write_json(self.directory() / "session.json", self.current)
        write_json(self.root / "active.json", {"play_session_id": self.current["play_session_id"]})

    def new(self, label):
        label = text_field(label, "Session name")
        with self.lock:
            session_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            self.current = {"version": 1, "play_session_id": session_id, "label": label,
                            "created_at": utc_now(), "linked_save": None, "settings_snapshot_id": None}
            for folder in ("captures", "requests", "settings"):
                (self.directory() / folder).mkdir(parents=True, exist_ok=True)
            self._save()
            self.record("session_started", {"label": label})
            return self.status()

    def resume(self, session_id):
        with self.lock:
            data = read_json(self.directory(session_id) / "session.json")
            if data.get("play_session_id") != session_id:
                raise BridgeError("Play session metadata does not match its directory.")
            self.current = data
            self._save()
            return self.status()

    def status(self):
        with self.lock:
            return {**deepcopy(self.current), "directory": str(self.directory())}

    def sessions(self):
        items = []
        for path in self.root.glob("*/session.json"):
            if path.resolve().is_relative_to(self.root):
                data = read_json(path)
                items.append({k: data.get(k) for k in ("play_session_id", "label", "created_at", "linked_save")})
        return sorted(items, key=lambda item: item["created_at"], reverse=True)

    def rename(self, label):
        label = text_field(label, "Session name")
        with self.lock:
            self.current["label"] = label
            self._save()
            self.record("session_renamed", {"label": label})
            return self.status()

    def link_save(self, *, save_id=None, name="", note=""):
        name = text_field(name, "Save name", allow_empty=True)
        note = text_field(note, "Association note", 500, allow_empty=True)
        with self.lock:
            if save_id:
                selected = next((item for item in discover_saves(self.game_data) if item["save_id"] == save_id), None)
                if selected is None:
                    raise BridgeError("That save file is no longer available. Refresh the save list.")
            elif name:
                selected = {"name": name, "association": "manual_label"}
            else:
                selected = None
            self.current["linked_save"] = {**selected, "note": note, "linked_at": utc_now()} if selected else None
            self._save()
            self.record("save_linked", {"linked_save": self.current["linked_save"]})
            return self.status()

    def context(self):
        with self.lock:
            return {key: deepcopy(self.current.get(key)) for key in
                    ("play_session_id", "linked_save", "settings_snapshot_id")}

    def record(self, kind, data, *, session_id=None):
        with self.lock:
            session_id = session_id or self.current["play_session_id"]
            event = {"event_id": uuid.uuid4().hex, "at": utc_now(), "kind": kind,
                     "play_session_id": session_id, "data": deepcopy(data)}
            with (self.directory(session_id) / "events.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(event, ensure_ascii=False) + "\n")
            return event

    def events(self, session_id=None, limit=500):
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise BridgeError("History limit must be between 1 and 2000.")
        with self.lock:
            path = self.directory(session_id) / "events.jsonl"
            if not path.exists():
                return []
            from collections import deque
            with path.open(encoding="utf-8") as stream:
                lines = deque(stream, maxlen=limit)
            # Report damaged records rather than silently presenting an incomplete history.
            return [json.loads(line) for line in reversed(lines) if line.strip()]

    def record_request(self, current, *, finished=False):
        session_id = current.get("play_session_id", self.current["play_session_id"])
        suffix = ".result.json" if finished else ".json"
        write_json(self.directory(session_id) / "requests" / (current["request_id"] + suffix), current)
        self.record("request_" + current["status"], current, session_id=session_id)

    def import_legacy(self, source):
        """Copy prior loose captures once; never move/delete the original evidence."""
        source = Path(source).resolve()
        marker = self.root / "legacy-import.json"
        if marker.exists() or not source.is_dir():
            return 0
        count = 0
        for metadata in sorted(source.glob("*.json")):
            if not re.fullmatch(r"[a-f0-9]{32}", metadata.stem):
                continue
            frame = read_json(metadata)
            if frame.get("frame_id") != metadata.stem:
                continue
            destination = self.directory() / "captures"
            saved_metadata = destination / metadata.name
            if saved_metadata.exists():
                continue
            paths = {}
            for key in ("full_path", "preview_path"):
                original = Path(frame[key]).resolve()
                if not original.is_relative_to(source) or not original.is_file():
                    raise BridgeError("A legacy capture references a missing or unexpected image.")
                copied = destination / original.name
                shutil.copy2(original, copied)
                paths[key] = str(copied)
            frame.update(paths)
            frame.update({"play_session_id": self.current["play_session_id"], "linked_save": None,
                          "settings_snapshot_id": None, "request_id": None, "reason": "legacy_import"})
            write_json(saved_metadata, frame)
            self.record("capture_imported", frame)
            count += 1
        write_json(marker, {"source": str(source), "imported": count, "at": utc_now(),
                            "play_session_id": self.current["play_session_id"]})
        return count
