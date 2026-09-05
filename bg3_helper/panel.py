"""A native second-screen panel; inference stays in the active agent session."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from .core import Bridge, BridgeError
from .transport import create_server, request
from .windows import Hotkeys, WindowsDesktop
from .session import SessionRequests, TERMINAL


def run_panel(runtime: Path, test_target=False):
    desktop = WindowsDesktop(test_target=test_target)
    runtime.mkdir(parents=True, exist_ok=True)
    try:
        request(runtime, "status")
    except BridgeError:
        pass
    else:
        raise BridgeError("A companion is already running for this runtime directory.")
    bridge = Bridge(desktop, runtime / "captures")
    session = SessionRequests(bridge, runtime)
    server, descriptor = create_server(bridge)
    (runtime / "connection.json").write_text(json.dumps(descriptor), encoding="utf-8")
    threading.Thread(target=server.serve_forever, daemon=True).start()

    root = tk.Tk()
    root.title("BG3 Companion" + (" — Test" if test_target else ""))
    root.configure(bg="#111722")
    root.minsize(540, 920)
    # Start on the non-primary display when one is available, without changing display settings.
    import mss
    with mss.mss() as grabber:
        screens = grabber.monitors[1:]
    screen = next((m for m in screens if m["left"] != 0 or m["top"] != 0), screens[0])
    root.geometry("560x1000")
    root.update_idletasks()
    hwnd = desktop.user.GetAncestor(root.winfo_id(), 2)
    # Tk's negative geometry offsets mean distance from the right/bottom, not
    # negative virtual-desktop coordinates. Position explicitly in physical pixels.
    desktop.gui.SetWindowPos(hwnd, 0, screen["left"] + 35, screen["top"] + 60, 0, 0, 0x0015)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TButton", font=("Segoe UI", 11), padding=9)
    work = queue.Queue()
    ui = queue.Queue()
    closing = threading.Event()

    def worker():
        while not closing.is_set():
            try:
                function = work.get(timeout=0.3)
            except queue.Empty:
                continue
            try:
                function()
                bridge.last_error = ""
            except Exception as exc:
                bridge.last_error = str(exc)

    threading.Thread(target=worker, daemon=True).start()

    def toggle():
        if bridge.armed:
            bridge.stop()
        else:
            revision = bridge.stop_revision
            work.put(lambda: bridge.arm(expected_stop_revision=revision))

    hotkeys = Hotkeys(lambda: work.put(bridge.capture), toggle, bridge.stop)
    body = tk.Frame(root, bg="#111722", padx=22, pady=18)
    body.pack(fill="both", expand=True)

    def label(text, size=11, color="#aebbd0", **kwargs):
        widget = tk.Label(body, text=text, bg="#111722", fg=color,
                          font=("Segoe UI", size), justify="left", anchor="w", **kwargs)
        widget.pack(fill="x", pady=(0, 10))
        return widget

    label("BG3 COMPANION", 10, "#87bea6")
    label("A second pair of eyes", 23, "#edf1f7")
    label("Play on your main display. Get help here.", wraplength=510)
    target_label = label("Looking for the game…", 12, "#ebcf92", wraplength=500)

    input_card = tk.Frame(body, bg="#1a2332", padx=12, pady=10,
                          highlightthickness=2, highlightbackground="#46566d")
    input_card.pack(fill="x", pady=(0, 16))
    input_state = tk.BooleanVar(value=False)

    def switch_image(enabled):
        # Keep a real Checkbutton for keyboard focus/Space; draw its switch face.
        picture = Image.new("RGBA", (324, 132))
        draw = ImageDraw.Draw(picture)
        draw.rounded_rectangle((0, 0, 323, 131), radius=66,
                               fill="#32c797" if enabled else "#536279")
        left = 198 if enabled else 12
        draw.ellipse((left, 12, left + 108, 120), fill="#ffffff")
        return ImageTk.PhotoImage(picture.resize((108, 44), Image.Resampling.LANCZOS))

    off_image, on_image = switch_image(False), switch_image(True)

    def update_input_switch():
        # Read the permission directly, so an old status snapshot cannot undo STOP visually.
        armed = bridge.armed
        background = "#153b32" if armed else "#1a2332"
        foreground = "#b2f5d8" if armed else "#dce4ee"
        input_state.set(armed)
        input_card.configure(bg=background, highlightbackground="#32c797" if armed else "#46566d")
        input_switch.configure(text="  INPUT ON" if armed else "  INPUT OFF", bg=background,
                               fg=foreground, activebackground=background, activeforeground=foreground,
                               selectcolor=background, highlightbackground=background)
        seconds = max(0, int(bridge.armed_until - bridge.clock()))
        input_label.configure(text=(f"Smart next move may act · {seconds // 60}:{seconds % 60:02d} remaining" if armed
                                    else "Advice only · game input disabled"), bg=background, fg=foreground)

    def toggle_from_panel():
        toggle()
        # Enabling is asynchronous. Show ON only after the bridge accepts it.
        update_input_switch()

    input_switch = tk.Checkbutton(input_card, text="  INPUT OFF", variable=input_state,
                                  command=toggle_from_panel, indicatoron=False, image=off_image,
                                  selectimage=on_image, compound="left", anchor="w", cursor="hand2",
                                  font=("Segoe UI", 20, "bold"), bg="#1a2332", fg="#dce4ee",
                                  relief="flat", offrelief="flat", borderwidth=0, padx=2, pady=3,
                                  highlightthickness=2, highlightbackground="#1a2332",
                                  highlightcolor="#c4e3ff", takefocus=True)
    input_switch.pack(fill="x")
    input_switch.bind("<Return>", lambda _event: (input_switch.invoke(), "break")[-1])
    input_label = tk.Label(input_card, text="Advice only · game input disabled", bg="#1a2332", fg="#dce4ee",
                           font=("Segoe UI", 10), anchor="w", padx=4, pady=5, wraplength=465)
    input_label.pack(fill="x")

    label("What are you trying to do? (optional)", 10)
    objective = tk.StringVar()
    goal_entry = tk.Entry(body, textvariable=objective, bg="#1a2332", fg="#e0e7f0",
                         insertbackground="white", font=("Segoe UI", 11), relief="flat")
    goal_entry.pack(fill="x", ipady=7, pady=(0, 10))

    def submit(kind):
        goal = objective.get().strip()
        revision = bridge.stop_revision
        work.put(lambda: session.submit(kind, goal, return_focus=lambda target: desktop.return_focus(target, hwnd),
                                        expected_stop_revision=revision))

    smart_row = tk.Frame(body, bg="#111722")
    smart_row.pack(fill="x", pady=(0, 8))
    explain_button = ttk.Button(smart_row, text="Explain screen", command=lambda: submit("explain"))
    explain_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
    smart_button = ttk.Button(smart_row, text="Smart next move", command=lambda: submit("smart"))
    smart_button.pack(side="left", fill="x", expand=True, padx=(5, 0))

    row = tk.Frame(body, bg="#111722")
    row.pack(fill="x", pady=(2, 10))
    ttk.Button(row, text="Capture only", command=lambda: work.put(bridge.capture)).pack(side="left")
    tk.Button(row, text="STOP", command=bridge.stop, bg="#963d46", fg="white",
              activebackground="#b64c58", relief="flat", font=("Segoe UI", 11, "bold"), padx=16, pady=9).pack(side="right")
    session_label = label("Connecting to Codex…", 10, "#ebcf92", wraplength=500)
    label("Optional shortcuts: hold Ctrl+Alt, then Numpad 0 to capture,\n1 to toggle input, or 2 to stop. Num Lock on.", 10, wraplength=510)
    preview = tk.Label(body, text="Your next game capture appears here", bg="#1a2332", fg="#8391a7",
                       height=6, font=("Segoe UI", 11))
    preview.pack(fill="x", pady=(0, 10))
    frame_label = label("No frame captured", 10, wraplength=510)
    advice = tk.Text(body, height=4, wrap="word", bg="#1a2332", fg="#e0e7f0",
                     relief="flat", padx=12, pady=12, font=("Segoe UI", 11))
    advice.pack(fill="both", expand=True, pady=(0, 10))
    error_label = label("", 10, "#efad9c", wraplength=500)
    last_frame = None
    last_note = None
    poll_running = False

    def poll_status():
        try:
            ui.put(bridge.status())
        except Exception as exc:
            ui.put({"poll_error": str(exc)})

    def refresh():
        nonlocal last_frame, last_note, poll_running
        if closing.is_set():
            return
        update_input_switch()
        # Never block Tk on a capture or OS call; STOP remains responsive.
        try:
            status = ui.get_nowait()
            poll_running = False
        except queue.Empty:
            status = None
        if status and "poll_error" not in status:
            target = status["target"]
            target_label.configure(text=(f"{target['title']}\n{target['rect']['width']} × {target['rect']['height']}" if target
                                         else "Waiting for Baldur’s Gate 3\nOpen the game and keep it visible."))
            session_status = status["session"]
            active = session_status["request"]
            busy = active is not None and active["status"] not in TERMINAL
            for button in (smart_button, explain_button):
                button.configure(state="disabled" if busy else "normal")
            messages = {"sending": "Sending your request to Codex…", "queued": "Waiting for Codex to finish its current turn…",
                        "working": "Codex is looking at the game…", "completed": "Result received from Codex.",
                        "cancelled": "Request cancelled. Press a button to start again.", "expired": "Request expired. Press a button to try again.",
                        "error": "Request could not finish. Check the message below."}
            session_label.configure(text=(messages.get(active["status"], active["status"]) if active
                                          else "Linked to Codex. Each button press requests help once." if session_status["thread_id"]
                                          else "Ask Codex to connect this companion to the conversation."))
            frame = status["latest"]
            if frame and frame["frame_id"] != last_frame:
                try:
                    with Image.open(frame["preview_path"]) as saved:
                        thumb = saved.copy()
                    thumb.thumbnail((510, 220), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb)
                    preview.configure(image=photo, text="", height=0)
                    preview.image = photo
                    last_frame = frame["frame_id"]
                    frame_label.configure(text=f"Captured {frame['captured_at'][11:19]} UTC · {frame['capture_ms']} ms\nFrame {last_frame[:12]}")
                except OSError as exc:
                    bridge.last_error = str(exc)
            if status["note"] != last_note:
                advice.configure(state="normal")
                advice.delete("1.0", "end")
                advice.insert("1.0", status["note"])
                advice.configure(state="disabled")
                last_note = status["note"]
            error_label.configure(text=status["last_error"] or "\n".join(hotkeys.errors))
        if not poll_running:
            poll_running = True
            threading.Thread(target=poll_status, daemon=True).start()
        root.after(500, refresh)

    def close():
        bridge.stop()
        closing.set()
        hotkeys.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    try:
        root.mainloop()
    finally:
        bridge.stop()
        closing.set()
        hotkeys.close()
        server.shutdown()
        server.server_close()
        # Invalidate the session descriptor without deleting user artifacts.
        (runtime / "connection.json").write_text("{}", encoding="utf-8")
