from pathlib import Path

import pytest

from bg3_helper.core import Bridge, BridgeError
from bg3_helper.session import SessionRequests, queue_message
from test_core import Desktop, proposal


@pytest.fixture
def linked(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    desktop = Desktop()
    now = [100.0]
    bridge = Bridge(desktop, tmp_path / "captures", clock=lambda: now[0])
    deliveries = []
    session = SessionRequests(bridge, tmp_path, sender=lambda *args: deliveries.append(args), clock=lambda: now[0])
    session.connect("11111111-1111-4111-8111-111111111111")
    return bridge, desktop, session, deliveries, now


def test_explain_queues_image_and_returns_result_to_panel(linked):
    bridge, desktop, session, deliveries, _ = linked
    item = session.submit("explain", "What is visible?")
    assert item["status"] == "queued"
    assert not item["allow_actions"]
    assert len(deliveries) == 1
    assert Path(deliveries[0][2]).is_file()
    assert desktop.sent == []
    assert session.claim(item["request_id"])["status"] == "working"
    assert session.finish(item["request_id"], "Open the inventory to inspect your equipment.") == {"completed": True}
    assert bridge.note == "Open the inventory to inspect your equipment."
    assert session.status()["request"]["status"] == "completed"


@pytest.mark.parametrize("kind", ["smart", "explain"])
def test_allowing_input_later_does_not_upgrade_advice_request(linked, kind):
    bridge, desktop, session, _, _ = linked
    item = session.submit(kind)
    bridge.arm()
    with pytest.raises(BridgeError, match="advice only"):
        bridge.act(proposal(bridge, smart_request_id=item["request_id"]))
    assert not desktop.sent


def test_smart_request_limits_gestures_and_deduplicates(linked):
    bridge, desktop, session, _, _ = linked
    bridge.arm()
    item = session.submit("smart", "Open inventory")
    assert item["allow_actions"]
    for i in range(3):
        action = proposal(bridge, request_id=f"gesture-{i}", smart_request_id=item["request_id"])
        result = bridge.act(action)
        assert result["status"] == "input_sent"
        assert bridge.act(action) == result
    with pytest.raises(BridgeError, match="three gestures"):
        bridge.act(proposal(bridge, request_id="fourth", smart_request_id=item["request_id"]))
    assert len(desktop.sent) == 3


def test_stop_revokes_request_even_after_rearming(linked):
    bridge, desktop, session, _, _ = linked
    bridge.arm()
    item = session.submit("smart")
    bridge.stop()
    bridge.arm()
    with pytest.raises(BridgeError, match="cancelled"):
        bridge.act(proposal(bridge, smart_request_id=item["request_id"]))
    assert not desktop.sent


def test_old_and_expired_requests_cannot_act(linked):
    bridge, desktop, session, _, now = linked
    bridge.arm()
    item = session.submit("smart")
    now[0] += 301
    bridge.capture()
    with pytest.raises(BridgeError, match="expired"):
        bridge.act(proposal(bridge, smart_request_id=item["request_id"]))
    second = session.submit("smart")
    assert second["request_id"] != item["request_id"]
    with pytest.raises(BridgeError, match="no longer current"):
        session.claim(item["request_id"])
    assert not desktop.sent


def test_double_press_does_not_queue_twice(linked):
    _, _, session, deliveries, _ = linked
    session.submit("smart")
    with pytest.raises(BridgeError, match="already waiting"):
        session.submit("smart")
    assert len(deliveries) == 1


def test_connection_test_does_not_capture_or_enable_input(linked):
    bridge, desktop, session, deliveries, _ = linked
    item = session.submit("connection_test")
    assert bridge.frame is None
    assert not item["allow_actions"]
    assert deliveries[0][2] is None
    assert not desktop.sent


def test_request_requires_tag_on_actions(linked):
    bridge, desktop, session, _, _ = linked
    bridge.arm()
    session.submit("smart")
    with pytest.raises(BridgeError, match="include its smart_request_id"):
        bridge.act(proposal(bridge))
    assert not desktop.sent


def test_failed_delivery_never_retries_or_allows_late_action(linked):
    bridge, desktop, session, _, _ = linked
    calls = []
    def failing(*args):
        calls.append(args)
        raise BridgeError("Delivery is uncertain.")
    session.sender = failing
    bridge.arm()
    with pytest.raises(BridgeError, match="uncertain"):
        session.submit("smart")
    item = session.status()["request"]
    assert item["status"] == "error"
    assert len(calls) == 1
    with pytest.raises(BridgeError, match="error"):
        session.claim(item["request_id"])
    assert not desktop.sent


def test_stop_cancels_queued_and_inflight_capture(linked):
    bridge, desktop, session, deliveries, _ = linked
    revision = bridge.stop_revision
    bridge.stop()
    with pytest.raises(BridgeError, match="cancelled before"):
        session.submit("smart", expected_stop_revision=revision)
    capture = desktop.capture
    def interrupted(target):
        result = capture(target)
        bridge.stop()
        return result
    desktop.capture = interrupted
    with pytest.raises(BridgeError, match="cancelled during"):
        session.submit("smart")
    assert not deliveries


def test_stop_between_capture_and_request_creation_stays_cancelled(linked, monkeypatch):
    bridge, desktop, session, deliveries, _ = linked
    bridge.arm()
    def interrupted(_self):
        bridge.stop()
        return False
    monkeypatch.setattr(Bridge, "armed", property(interrupted))
    with pytest.raises(BridgeError, match="cancelled"):
        session.submit("smart")
    assert not deliveries
    assert not desktop.sent


def test_queue_uses_structured_argv_without_shell(monkeypatch):
    calls = []
    monkeypatch.setattr("bg3_helper.session.codex_command", lambda: ["codex.exe"])
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("Result", (), {"returncode": 0, "stdout": "Queued"})()
    monkeypatch.setattr("bg3_helper.session.subprocess.run", run)
    text = 'A request with "quotes", & and $(literal text)'
    assert queue_message("thread-id", text, "C:/Game Frames/test.png") == "Queued"
    assert calls[0][0] == ["codex.exe", "queue", "--thread", "thread-id", "--message", text,
                            "--image", "C:/Game Frames/test.png"]
    assert calls[0][1]["shell"] is False
