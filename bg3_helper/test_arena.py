"""Disposable native test surface. Only used by the explicit --test-target mode."""
import json
from pathlib import Path
import threading
import time
import tkinter as tk

from .core import Bridge
from .windows import WindowsDesktop


def main():
    desktop = WindowsDesktop(test_target=True)
    root = tk.Tk()
    root.title("BG3 Helper Test Arena")
    root.geometry("900x600+300+260")
    root.configure(bg="#192639")
    root.update_idletasks()
    hwnd = desktop.user.GetAncestor(root.winfo_id(), 2)
    if not desktop.user.SetPropW(hwnd, "BG3HelperTestArena", 1):
        raise RuntimeError("Could not mark the disposable test window.")
    counts = {"clicks": 0, "keys": 0, "scrolls": 0}
    output = Path(__file__).resolve().parent.parent / ".runtime" / "self-test"
    tk.Label(root, text="BG3 Helper · Disposable test arena", bg="#192639", fg="white",
             font=("Segoe UI", 24)).pack(pady=25)
    tk.Label(root, text="Software capture, coordinate mapping, and input verification\nNo game or save is involved.",
             bg="#192639", fg="#b7c9df", font=("Segoe UI", 13)).pack(pady=5)
    count_label = tk.Label(root, text="Clicks: 0    Keys: 0    Scrolls: 0", bg="#192639", fg="#e6c997",
                          font=("Segoe UI", 18))
    count_label.pack(pady=20)

    def count(kind):
        counts[kind] += 1
        count_label.configure(text=f"Clicks: {counts['clicks']}    Keys: {counts['keys']}    Scrolls: {counts['scrolls']}")

    target = tk.Button(root, text="Test click", command=lambda: count("clicks"), bg="#78bea5", fg="#10271f",
                       font=("Segoe UI", 17), padx=55, pady=20)
    target.pack(pady=10)
    root.bind("<KeyPress-i>", lambda e: count("keys"))
    root.bind("<MouseWheel>", lambda e: count("scrolls"))
    status = tk.Label(root, text="Waiting for self-test", bg="#192639", fg="white", font=("Segoe UI", 12), wraplength=800)
    status.pack(pady=15)

    def start_test():
        status.configure(text="Testing local capture and a click, key, and scroll…")
        button.configure(state="disabled")
        center = (target.winfo_rootx() + target.winfo_width() // 2,
                  target.winfo_rooty() + target.winfo_height() // 2)
        initial = dict(counts)

        def run():
            bridge = Bridge(desktop, output)
            result = {}
            try:
                bridge.arm()
                before = bridge.capture()
                r = before["window"]["rect"]
                x = (center[0] - r["left"]) * before["image_width"] / r["width"]
                y = (center[1] - r["top"]) * before["image_height"] / r["height"]
                action = {"request_id": "test-click", "frame_id": before["frame_id"], "kind": "click", "x": x, "y": y}
                clicked = bridge.act(action)
                duplicate = bridge.act(action)
                if clicked["status"] != "input_sent":
                    raise RuntimeError(str(clicked))
                frame = bridge.capture()
                keyed = bridge.act({"request_id": "test-key", "frame_id": frame["frame_id"], "kind": "key", "key": "i"})
                frame = bridge.capture()
                scrolled = bridge.act({"request_id": "test-scroll", "frame_id": frame["frame_id"], "kind": "scroll", "x": x, "y": y, "steps": 1})
                time.sleep(0.2)
                delta = {k: counts[k] - initial[k] for k in counts}
                passed = (delta == {"clicks": 1, "keys": 1, "scrolls": 1} and duplicate == clicked and
                          keyed["status"] == "input_sent" and scrolled["status"] == "input_sent")
                result = {"passed": passed, "observed_events": delta, "duplicate_replayed": delta["clicks"] != 1,
                          "before": before, "after": scrolled.get("after"), "key": keyed["status"], "scroll": scrolled["status"]}
            except Exception as exc:
                result = {"passed": False, "error": str(exc)}
            finally:
                bridge.stop()
            output.mkdir(parents=True, exist_ok=True)
            (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            root.after(0, lambda: status.configure(text="PASS · one click, one key, one scroll; duplicate did not replay" if result["passed"] else "FAILED · " + result.get("error", str(result))))
            root.after(0, lambda: button.configure(state="normal"))

        root.after(700, lambda: threading.Thread(target=run, daemon=True).start())

    button = tk.Button(root, text="Run bridge self-test", command=start_test,
                       font=("Segoe UI", 13), padx=20, pady=10)
    button.pack(pady=10)
    root.mainloop()


if __name__ == "__main__":
    main()
