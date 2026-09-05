"""Native history, play-session, and setup dialogs; I/O stays off the Tk thread."""
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .settings import PROFILE_DEFAULTS, RESOLUTIONS, UPSCALING
from .transport import request


def job(window, function, success, message):
    results = queue.Queue()
    message.set("Working…")
    def run():
        try:
            results.put((True, function()))
        except Exception as exc:
            results.put((False, str(exc)))
    threading.Thread(target=run, daemon=True).start()
    def poll():
        if not window.winfo_exists():
            return
        try:
            ok, value = results.get_nowait()
        except queue.Empty:
            window.after(100, poll)
            return
        if ok:
            message.set("")
            success(value)
        else:
            message.set(value)
    window.after(100, poll)


def dialog(root, title, size, position):
    window = tk.Toplevel(root)
    window.title(title)
    window.geometry(size)
    window.transient(root)
    # Do not grab input: the main companion's STOP must remain available.
    body = ttk.Frame(window, padding=18)
    body.pack(fill="both", expand=True)
    message = tk.StringVar()
    ttk.Label(body, textvariable=message, wraplength=850, foreground="#a02b32").pack(side="bottom", fill="x", pady=(12, 0))
    position(window)
    return window, body, message


def session_dialog(root, runtime, position):
    window, body, message = dialog(root, "BG3 · Play session and save", "780x490", position)
    ttk.Label(body, text="Keep captures and decisions with the play session they belong to.").pack(anchor="w", pady=(0, 12))
    name = tk.StringVar()
    ttk.Label(body, text="Play session name").pack(anchor="w")
    ttk.Entry(body, textvariable=name).pack(fill="x", pady=(4, 12))
    saved = ttk.Combobox(body, state="readonly")
    saved.pack(fill="x", pady=(0, 8))
    rows = []
    saves = []
    save_choice = ttk.Combobox(body, state="readonly")
    ttk.Label(body, text="Linked save — a reference; this does not load or change the save").pack(anchor="w", pady=(8, 4))
    save_choice.pack(fill="x")
    manual_name, note = tk.StringVar(), tk.StringVar()
    ttk.Label(body, text="Manual save name (when no file is selected)").pack(anchor="w", pady=(10, 4))
    manual_entry = ttk.Entry(body, textvariable=manual_name)
    manual_entry.pack(fill="x")
    ttk.Label(body, text="Association note (optional)").pack(anchor="w", pady=(10, 4))
    ttk.Entry(body, textvariable=note).pack(fill="x")
    controls = ttk.Frame(body)
    controls.pack(fill="x", pady=14)

    def selected_save(_event=None):
        manual_entry.configure(state="normal" if save_choice.current() == 1 else "disabled")

    def populate(data):
        history, listing = data
        rows[:] = history["sessions"]
        saves[:] = listing["saves"]
        current = history["current"]
        name.set(current["label"])
        saved.configure(values=[f"{item['label']} · {item['created_at'][:16].replace('T', ' ')}" for item in rows])
        saved.current(next(i for i, item in enumerate(rows) if item["play_session_id"] == current["play_session_id"]))
        save_choice.configure(values=["No save linked", "Use a manual save name"] +
                              [f"{item['name']} · {item['profile']} · {item['modified_at'][:16]}" for item in saves])
        linked = current["linked_save"]
        index = 0
        if linked:
            index = next((i + 2 for i, item in enumerate(saves) if item["save_id"] == linked.get("save_id")), 1)
        save_choice.current(index)
        manual_name.set(linked["name"] if linked else "")
        note.set(linked.get("note", "") if linked else "")
        selected_save()

    def refresh():
        job(window, lambda: (request(runtime, "history", {"limit": 1}), request(runtime, "saves")), populate, message)

    def changed(_value):
        refresh()

    def save_link():
        label, index = name.get(), save_choice.current()
        body = {"operation": "link", "name": manual_name.get() if index == 1 else "", "note": note.get()}
        if index >= 2:
            body["save_id"] = saves[index - 2]["save_id"]
        def save():
            request(runtime, "play", {"operation": "rename", "label": label})
            return request(runtime, "play", body)
        job(window, save, changed, message)

    def new():
        label = name.get()
        job(window, lambda: request(runtime, "play", {"operation": "new", "label": label}), changed, message)

    def resume():
        if saved.current() >= 0:
            session_id = rows[saved.current()]["play_session_id"]
            job(window, lambda: request(runtime, "play", {"operation": "resume", "session_id": session_id}), changed, message)

    save_choice.bind("<<ComboboxSelected>>", selected_save)
    for text, command in (("Save name & link", save_link), ("New play session", new), ("Resume selected", resume), ("Refresh saves", refresh)):
        ttk.Button(controls, text=text, command=command).pack(side="left", padx=(0, 5))
    refresh()


def event_summary(event):
    data, kind = event["data"], event["kind"]
    if kind.startswith("capture"):
        return f"{data.get('reason', 'capture')} · {data.get('image_width')} × {data.get('image_height')}"
    if kind.startswith("request_"):
        return f"{data['kind']} · {data.get('result') or data.get('objective', '')}"[:150]
    if kind.startswith("action_"):
        return f"{data['request']['kind']} · {data.get('result', {}).get('status', 'requested')}"
    if kind == "settings_snapshot":
        return f"{data.get('configured_resolution') or 'Resolution unknown'} · {data['profile']['label']}"
    if kind == "settings_observed":
        return "; ".join(f"{key}: {value}" for key, value in data["values"].items())[:150]
    if kind == "save_linked":
        return (data.get("linked_save") or {}).get("name", "Save link cleared")
    if kind == "profile_updated":
        return data["after"]["active"] + " · " + data.get("note", "")
    return data.get("label", kind)


def history_dialog(root, runtime, position):
    window, body, message = dialog(root, "BG3 · Capture and activity history", "1150x760", position)
    top = ttk.Frame(body)
    top.pack(fill="x", pady=(0, 12))
    choices = ttk.Combobox(top, state="readonly", width=55)
    choices.pack(side="left", fill="x", expand=True)
    pane = ttk.Panedwindow(body, orient="horizontal")
    pane.pack(fill="both", expand=True)
    listing, detail = ttk.Frame(pane), ttk.Frame(pane)
    pane.add(listing, weight=1)
    pane.add(detail, weight=1)
    tree = ttk.Treeview(listing, columns=("time", "kind", "summary"), show="headings", selectmode="browse")
    for column, label, width in (("time", "Time (UTC)", 125), ("kind", "Event", 125), ("summary", "Summary", 275)):
        tree.heading(column, text=label)
        tree.column(column, width=width, minwidth=70)
    scrollbar = ttk.Scrollbar(listing, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    tabs = ttk.Notebook(detail)
    tabs.pack(fill="both", expand=True)
    preview = ttk.Label(tabs, text="Select a capture or request to preview it.", anchor="center")
    raw = tk.Text(tabs, wrap="word", font=("Consolas", 10))
    tabs.add(preview, text="Preview")
    tabs.add(raw, text="Details")
    sessions, events = [], {}
    selected_directory = [None]

    def populate(data):
        sessions[:] = data["sessions"]
        choices.configure(values=[f"{item['label']} · {item['created_at'][:16].replace('T', ' ')}" for item in sessions])
        choices.current(next(i for i, item in enumerate(sessions) if item["play_session_id"] == data["selected_session_id"]))
        selected_directory[0] = Path(data["directory"])
        preview.configure(image="", text="Select a capture or request to preview it.")
        preview.image = None
        raw.configure(state="normal")
        raw.delete("1.0", "end")
        raw.configure(state="disabled")
        tree.delete(*tree.get_children())
        events.clear()
        for event in data["events"]:
            events[event["event_id"]] = event
            tree.insert("", "end", iid=event["event_id"], values=(event["at"][5:19].replace("T", " "), event["kind"], event_summary(event)))
        message.set(f"Showing {len(events)} recent events. All captures and records remain in the session folder.")

    def refresh(_event=None):
        index = choices.current()
        session_id = sessions[index]["play_session_id"] if index >= 0 else None
        job(window, lambda: request(runtime, "history", {"session_id": session_id, "limit": 500}), populate, message)

    def select(_event=None):
        selection = tree.selection()
        if not selection:
            return
        event = events[selection[0]]
        raw.configure(state="normal")
        raw.delete("1.0", "end")
        raw.insert("1.0", json.dumps(event, indent=2, ensure_ascii=False))
        raw.configure(state="disabled")
        data = event["data"]
        frame = data.get("frame") or data.get("before") or data.get("result", {}).get("after") or data
        path = frame.get("preview_path") or (data.get("path") if event["kind"] == "crop" else None)
        preview.configure(image="", text="This event has no screenshot. See Details for its record.")
        if path and selected_directory[0] and Path(path).resolve().is_relative_to(selected_directory[0].resolve()):
            try:
                with Image.open(path) as source:
                    picture = source.copy()
                picture.thumbnail((560, 540), Image.Resampling.LANCZOS)
                preview.image = ImageTk.PhotoImage(picture)
                preview.configure(image=preview.image, text="")
            except OSError as exc:
                message.set(str(exc))

    def open_files():
        if selected_directory[0]:
            os.startfile(selected_directory[0])

    ttk.Button(top, text="Refresh", command=refresh).pack(side="left", padx=6)
    ttk.Button(top, text="Open files", command=open_files).pack(side="left")
    choices.bind("<<ComboboxSelected>>", refresh)
    tree.bind("<<TreeviewSelect>>", select)
    refresh()


def setup_dialog(root, runtime, position):
    window, body, message = dialog(root, "BG3 · Setup profiles and settings", "900x800", position)
    ttk.Label(body, text="Starter profiles · targets are preferences, not benchmark results.").pack(anchor="w", pady=(0, 10))
    names = list(PROFILE_DEFAULTS)
    choice = ttk.Combobox(body, values=[PROFILE_DEFAULTS[key]["label"] for key in names], state="readonly")
    choice.pack(fill="x", pady=(0, 12))
    override_summary = tk.StringVar()
    ttk.Label(body, textvariable=override_summary, wraplength=840).pack(anchor="w", pady=(0, 8))
    bank = {}
    variables = {key: tk.StringVar() for key in ("target_fps", "resolution", "upscaling", "note")}
    flags = {key: tk.BooleanVar() for key in ("borderless", "background_audio", "unlock_mouse")}
    fields = ttk.Frame(body)
    fields.pack(fill="x")
    for row, (key, label, options) in enumerate((
            ("target_fps", "Target FPS", None), ("resolution", "Game resolution", RESOLUTIONS),
            ("upscaling", "Upscaling / antialiasing", UPSCALING))):
        ttk.Label(fields, text=label).grid(row=row, column=0, sticky="w", padx=(0, 15), pady=5)
        widget = ttk.Combobox(fields, textvariable=variables[key], values=options, state="readonly") if options else ttk.Entry(fields, textvariable=variables[key])
        widget.grid(row=row, column=1, sticky="ew", pady=5)
    fields.columnconfigure(1, weight=1)
    for key, label in (("borderless", "Use borderless mode"), ("background_audio", "Keep audio playing when unfocused"),
                       ("unlock_mouse", "Allow moving the mouse to the companion display")):
        ttk.Checkbutton(body, text=label, variable=flags[key]).pack(anchor="w", pady=4)
    ttk.Label(body, text="Override note (optional)").pack(anchor="w", pady=(8, 4))
    ttk.Entry(body, textvariable=variables["note"]).pack(fill="x")
    controls = ttk.Frame(body)
    controls.pack(fill="x", pady=12)
    ttk.Label(body, text="Saving a profile does not change BG3. Use Smart system setup to apply it when INPUT is ON.", wraplength=840).pack(anchor="w", pady=(0, 14))
    baseline = tk.Text(body, height=12, wrap="word", font=("Segoe UI", 11))
    baseline.pack(fill="both", expand=True)

    def load_profile(_event=None, defaults=False):
        if choice.current() < 0:
            return
        key = names[choice.current()]
        profile = PROFILE_DEFAULTS[key] if defaults else bank.get(key, PROFILE_DEFAULTS[key])
        labels = {"target_fps": "FPS cap", "resolution": "resolution", "upscaling": "upscaling",
                  "borderless": "borderless", "background_audio": "background audio", "unlock_mouse": "free mouse"}
        overrides = "; ".join(f"{labels[field]}: {value}" for field, value in profile.get("overrides", {}).items())
        override_summary.set("Starter defaults loaded; save to keep them." if defaults else
                             f"Saved overrides: {overrides or 'none'} · revision {profile.get('revision', 0)}")
        for field in ("target_fps", "resolution", "upscaling"):
            variables[field].set(str(profile[field]))
        variables["note"].set("Reset to starter defaults" if defaults else profile.get("note", ""))
        for field in flags:
            flags[field].set(profile[field])

    def populate(data):
        bank.clear()
        bank.update(data["profiles"]["profiles"])
        choice.current(names.index(data["profiles"]["active"]))
        load_profile()
        snapshot = data["latest_snapshot"]
        lines = ["Current settings baseline"]
        if snapshot:
            lines += ["Captured: " + snapshot["captured_at"], "Configured game resolution: " + (snapshot["configured_resolution"] or "Unknown")]
            target = snapshot.get("target")
            if target:
                lines.append(f"Game window: {target['rect']['width']} × {target['rect']['height']}")
            for gpu in snapshot["system"].get("gpus", []):
                lines.append(f"GPU: {gpu['name']} · driver {gpu['driver']}")
            lines += snapshot["warnings"]
        else:
            lines.append("No baseline yet. Read current settings to save one locally.")
        lines.append("\nMenu observations (screenshot time)")
        for key, item in data["observations"].items():
            captured_at = item.get("captured_at", item["observed_at"])
            lines.append(f"{key}: {item['value']} ({captured_at[:19]})")
            if item.get("note"):
                lines.append("  " + item["note"])
        if not data["observations"]:
            lines.append("None recorded yet. Smart system setup can inspect the menu.")
        baseline.configure(state="normal")
        baseline.delete("1.0", "end")
        baseline.insert("1.0", "\n".join(lines))
        baseline.configure(state="disabled")

    def refresh():
        job(window, lambda: request(runtime, "settings"), populate, message)

    def save():
        if choice.current() < 0:
            return
        try:
            values = {"target_fps": int(variables["target_fps"].get()),
                      "resolution": variables["resolution"].get(), "upscaling": variables["upscaling"].get(),
                      **{key: value.get() for key, value in flags.items()}}
        except ValueError:
            message.set("Target FPS must be a whole number.")
            return
        profile_id, note = names[choice.current()], variables["note"].get()
        job(window, lambda: request(runtime, "profiles", {"profile_id": profile_id, "overrides": values, "note": note}), lambda _value: refresh(), message)

    def snapshot():
        job(window, lambda: request(runtime, "settings-snapshot"), lambda _value: refresh(), message)

    ttk.Button(controls, text="Save profile", command=save).pack(side="left", padx=(0, 6))
    ttk.Button(controls, text="Starter defaults", command=lambda: load_profile(defaults=True)).pack(side="left", padx=(0, 6))
    ttk.Button(controls, text="Read current settings", command=snapshot).pack(side="left")
    choice.bind("<<ComboboxSelected>>", load_profile)
    refresh()
