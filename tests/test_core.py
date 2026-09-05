from dataclasses import replace
import threading

import pytest
from PIL import Image

from bg3_helper.core import Bridge, BridgeError, Rect, Window, pixel_point


class Desktop:
    def __init__(self):
        self.window = Window(7, 42, "C:/Games/bg3.exe", "Baldur's Gate 3", Rect(-1920, 100, 1920, 1080))
        self.focused = True
        self.color = "#203040"
        self.sent = []
        self.failure = False

    def target(self):
        return self.window

    def capture(self, target):
        return Image.new("RGB", (target.rect.width, target.rect.height), self.color)

    def foreground(self, target):
        return self.focused

    def send(self, target, action, stopped):
        self.sent.append(action)
        if self.failure:
            raise OSError("Test input outcome is uncertain")


@pytest.fixture
def fixture(tmp_path):
    desktop = Desktop()
    now = [100.0]
    bridge = Bridge(desktop, tmp_path, clock=lambda: now[0])
    return bridge, desktop, now


def proposal(bridge, **changes):
    result = {"request_id": "turn-1", "frame_id": bridge.frame["frame_id"], "kind": "click", "x": 800, "y": 450}
    result.update(changes)
    return result


def test_coordinates_include_negative_monitor_origin_and_preview_scaling():
    assert pixel_point(800, 450, (1600, 900), Rect(-1920, 100, 1920, 1080)) == (-960, 640)
    assert pixel_point(1599, 899, (1600, 900), Rect(-1920, 100, 1920, 1080)) == (-2, 1178)


@pytest.mark.parametrize("x,y", [(-1, 0), (1600, 0), (0, 900), (float("nan"), 0), (float("inf"), 0), (True, 0), ("1", 2)])
def test_invalid_coordinates_rejected(x, y):
    with pytest.raises(BridgeError):
        pixel_point(x, y, (1600, 900), Rect(0, 0, 1920, 1080))


def test_capture_saves_native_and_preview_without_sending_input(fixture):
    bridge, desktop, _ = fixture
    frame = bridge.capture()
    assert Image.open(frame["full_path"]).size == (1920, 1080)
    assert Image.open(frame["preview_path"]).size == (1600, 900)
    assert desktop.sent == []
    assert not bridge.armed


@pytest.mark.parametrize("case", ["disabled", "expired_arm", "stale", "focus", "moved", "changed", "stopped", "old_frame"])
def test_unsafe_actions_do_not_reach_desktop(fixture, case):
    bridge, desktop, now = fixture
    bridge.arm()
    bridge.capture()
    action = proposal(bridge)
    if case == "disabled":
        bridge.armed_until = 0
    elif case == "expired_arm":
        now[0] += 601
    elif case == "stale":
        now[0] += 61
    elif case == "focus":
        desktop.focused = False
    elif case == "moved":
        desktop.window = replace(desktop.window, rect=Rect(0, 0, 1920, 1080))
    elif case == "changed":
        desktop.color = "white"
    elif case == "stopped":
        bridge.stop()
    elif case == "old_frame":
        bridge.capture()
    with pytest.raises(BridgeError):
        bridge.act(action)
    assert desktop.sent == []


def test_success_has_after_frame_and_duplicate_does_not_click_twice(fixture):
    bridge, desktop, _ = fixture
    bridge.arm()
    before = bridge.capture()
    action = proposal(bridge)
    result = bridge.act(action)
    assert result["status"] == "input_sent"
    assert result["after"]["frame_id"] != before["frame_id"]
    assert desktop.sent == [{"kind": "click", "point": (-960, 640), "button": "left"}]
    assert bridge.act(action) == result
    assert len(desktop.sent) == 1
    with pytest.raises(BridgeError, match="different action"):
        bridge.act(dict(action, x=200))
    with pytest.raises(BridgeError, match="latest frame"):
        bridge.act(dict(action, request_id="new-request"))


def test_unknown_input_result_disables_input_and_never_replays(fixture):
    bridge, desktop, _ = fixture
    bridge.arm()
    bridge.capture()
    desktop.failure = True
    action = proposal(bridge)
    result = bridge.act(action)
    assert result["status"] == "outcome_unknown"
    assert not bridge.armed
    assert bridge.act(action) == result
    assert len(desktop.sent) == 1


@pytest.mark.parametrize("changes", [
    {"kind": "key", "key": "alt+f4"}, {"kind": "key", "key": "f5"},
    {"kind": "scroll", "steps": 0}, {"kind": "scroll", "steps": 7},
    {"kind": "click", "button": "other"}, {"kind": "type", "text": "anything"},
])
def test_bounded_gestures(fixture, changes):
    bridge, desktop, _ = fixture
    bridge.arm()
    bridge.capture()
    with pytest.raises(BridgeError):
        bridge.act(proposal(bridge, **changes))
    assert not desktop.sent


def test_crop_keeps_original_action_space(fixture):
    bridge, _, _ = fixture
    before = bridge.capture()
    crop = bridge.crop(1600, 900, 300, 150)
    assert Image.open(crop["path"]).size == (300, 150)
    assert bridge.frame == before
    with pytest.raises(BridgeError):
        bridge.crop(1900, 1000, 100, 100)


def test_stop_does_not_wait_for_capture_lock(fixture):
    bridge, _, _ = fixture
    bridge.arm()
    with bridge.lock:
        stopped = threading.Event()
        thread = threading.Thread(target=lambda: (bridge.stop(), stopped.set()))
        thread.start()
        assert stopped.wait(1)
    thread.join()
    assert not bridge.armed


def test_stop_cancels_queued_enable(fixture):
    bridge, _, _ = fixture
    revision = bridge.stop_revision
    bridge.stop()
    with pytest.raises(BridgeError, match="enable request was waiting"):
        bridge.arm(expected_stop_revision=revision)
    assert not bridge.armed


def test_stop_during_target_lookup_is_not_cleared_by_arm(fixture):
    bridge, desktop, _ = fixture
    def interrupted_lookup():
        bridge.stop()
        return desktop.window
    desktop.target = interrupted_lookup
    with pytest.raises(BridgeError, match="enable request was waiting"):
        bridge.arm()
    assert not bridge.armed
