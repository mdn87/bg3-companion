"""Software capture and short SendInput gestures on a physical Windows desktop."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import threading

from .core import BridgeError, Rect, Window
from .shortcuts import HOTKEY_BINDINGS


def enable_dpi():
    # Must happen before MSS or Tk initializes display coordinates.
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]


class WindowsDesktop:
    def __init__(self, *, test_target=False):
        enable_dpi()
        import win32gui
        import win32process
        self.gui, self.process = win32gui, win32process
        self.test_target = test_target
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                         wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.user.SendInput.restype = wintypes.UINT
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
        self.user.SetPropW.restype = wintypes.BOOL
        self.user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.GetPropW.restype = wintypes.HANDLE

    def executable(self, pid):
        handle = self.kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buf))
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(length)):
                return ""
            return buf.value
        finally:
            self.kernel.CloseHandle(handle)

    def _info(self, hwnd):
        if not self.gui.IsWindowVisible(hwnd) or self.gui.IsIconic(hwnd):
            return None
        _, pid = self.process.GetWindowThreadProcessId(hwnd)
        exe = self.executable(pid)
        name = Path(exe).name.lower()
        title = self.gui.GetWindowText(hwnd)
        eligible = name in {"bg3.exe", "bg3_dx11.exe"}
        if self.test_target:
            eligible = (name in {"python.exe", "pythonw.exe"} and
                        title == "BG3 Helper Test Arena" and
                        self.user.GetPropW(hwnd, "BG3HelperTestArena") == 1)
        if not eligible:
            return None
        left, top, right, bottom = self.gui.GetClientRect(hwnd)
        origin = self.gui.ClientToScreen(hwnd, (left, top))
        if right <= left or bottom <= top:
            return None
        return Window(hwnd, pid, exe, title, Rect(*origin, right - left, bottom - top))

    def windows(self):
        matches = []
        def visit(hwnd, _):
            try:
                info = self._info(hwnd)
                if info:
                    matches.append(info)
            except Exception:
                pass  # An unrelated window can disappear during enumeration.
        self.gui.EnumWindows(visit, None)
        return matches

    def target(self):
        matches = self.windows()
        if len(matches) != 1:
            label = "test arena" if self.test_target else "Baldur's Gate 3"
            raise BridgeError(f"Expected one visible {label} window; found {len(matches)}. Open it and keep it unminimized.")
        return matches[0]

    def foreground(self, target):
        return self.gui.GetForegroundWindow() == target.hwnd

    def return_focus(self, target, source_hwnd):
        # Called only by the user's Smart next move button. Never interrupt a
        # different app the user has switched to while capture was running.
        if self.gui.GetForegroundWindow() != source_hwnd or self.target() != target:
            raise BridgeError("Focus changed since the companion button was pressed.")
        self.gui.SetForegroundWindow(target.hwnd)

    def _visible(self, target):
        # Screen-region capture includes occluders. Reject overlapping unrelated windows
        # before reading pixels, including windows on a monitor with a negative origin.
        bounds = target.rect
        above = []
        found = False
        def visit(hwnd, _):
            nonlocal found
            if hwnd == target.hwnd:
                found = True
            if found or not self.gui.IsWindowVisible(hwnd) or self.gui.IsIconic(hwnd):
                return
            try:
                cloaked = wintypes.DWORD()
                ctypes.windll.dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 14,
                                                          ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value:
                    return
                style = self.gui.GetWindowLong(hwnd, -20)
                # Cursor/highlight helpers can be transparent topmost windows
                # spanning the desktop. They do not intercept the game input.
                if style & 0x08080020 == 0x08080020:
                    return
                _, pid = self.process.GetWindowThreadProcessId(hwnd)
                if pid == target.pid:
                    return
                l, t, r, b = self.gui.GetWindowRect(hwnd)
                if (l < bounds.left + bounds.width and r > bounds.left and
                        t < bounds.top + bounds.height and b > bounds.top):
                    above.append(hwnd)
            except Exception:
                above.append(hwnd)
        self.gui.EnumWindows(visit, None)
        if above or not found:
            raise BridgeError("Another window overlaps the game. Uncover the game and capture again.")

    def capture(self, target):
        import mss
        from PIL import Image
        if self.target() != target:
            raise BridgeError("Target changed before capture.")
        self._visible(target)
        r = target.rect
        with mss.mss() as grabber:
            all_screens = grabber.monitors[0]
            if not (all_screens["left"] <= r.left and all_screens["top"] <= r.top and
                    r.left + r.width <= all_screens["left"] + all_screens["width"] and
                    r.top + r.height <= all_screens["top"] + all_screens["height"]):
                raise BridgeError("Game window extends outside the desktop. Move it fully onto a display.")
            frame = grabber.grab({"left": r.left, "top": r.top, "width": r.width, "height": r.height})
        self._visible(target)
        return Image.frombytes("RGB", frame.size, frame.bgra, "raw", "BGRX")

    def send(self, target, action, stopped):
        def check():
            if stopped.is_set() or self.target() != target or not self.foreground(target):
                raise BridgeError("Input stopped or game focus/geometry changed.")
            # User-held modifiers or buttons must not turn a simple gesture into a chord/drag.
            if any(self.user.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C, 1, 2, 4)):
                raise BridgeError("Release modifier keys and mouse buttons before input.")
        check()
        events = []
        if action["kind"] == "key":
            scan = self.user.MapVirtualKeyW(action["vk"], 0)
            events = [INPUT(type=1, ki=KEYBDINPUT(0, scan, flag, 0, 0)) for flag in (0x8, 0xA)]
        else:
            x, y = action["point"]
            hit = self.gui.WindowFromPoint((x, y))
            if self.user.GetAncestor(hit, 2) != target.hwnd:
                raise BridgeError("The requested point is covered by another window.")
            l, t = self.user.GetSystemMetrics(76), self.user.GetSystemMetrics(77)
            w, h = self.user.GetSystemMetrics(78), self.user.GetSystemMetrics(79)
            nx, ny = round((x - l) * 65535 / max(1, w - 1)), round((y - t) * 65535 / max(1, h - 1))
            events.append(INPUT(type=0, mi=MOUSEINPUT(nx, ny, 0, 0xC001, 0, 0)))
            if action["kind"] == "click":
                flags = {"left": (0x2, 0x4), "right": (0x8, 0x10), "middle": (0x20, 0x40)}[action["button"]]
                events.extend(INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, flag, 0, 0)) for flag in flags)
            elif action["kind"] == "scroll":
                events.append(INPUT(type=0, mi=MOUSEINPUT(0, 0, (action["steps"] * 120) & 0xFFFFFFFF, 0x800, 0, 0)))
        check()
        array = (INPUT * len(events))(*events)
        sent = self.user.SendInput(len(events), array, ctypes.sizeof(INPUT))
        if sent != len(events):
            # Release only this gesture if Windows accepted a partial input batch.
            if sent and action["kind"] in {"key", "click"}:
                release = (INPUT * 1)(events[-1])
                self.user.SendInput(1, release, ctypes.sizeof(INPUT))
            raise BridgeError(f"Windows accepted {sent}/{len(events)} input events. Result is uncertain.")


class Hotkeys:
    def __init__(self, capture, toggle, stop):
        self.callbacks = {1: capture, 2: toggle, 3: stop}
        self.errors = []
        self.thread_id = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        user = ctypes.windll.user32
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        for key_id, vk, label in HOTKEY_BINDINGS:
            if not user.RegisterHotKey(None, key_id, 0x4003, vk):
                self.errors.append(f"Could not register {label}; use the panel.")
        msg = wintypes.MSG()
        try:
            while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312 and msg.wParam in self.callbacks:
                    self.callbacks[msg.wParam]()
        finally:
            for key_id in self.callbacks:
                user.UnregisterHotKey(None, key_id)

    def close(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
