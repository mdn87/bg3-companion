import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from bg3_helper.transport import create_server, request
from bg3_helper.core import Bridge, BridgeError
from bg3_helper.session import SessionRequests
from bg3_helper.history import PlayHistory
from bg3_helper.settings import SettingsTracker
from test_core import Desktop


@pytest.fixture
def service(tmp_path):
    bridge = Bridge(Desktop(), tmp_path / "captures")
    server, info = create_server(bridge)
    (tmp_path / "connection.json").write_text(json.dumps(info))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield bridge, server, info, tmp_path
    server.shutdown()
    server.server_close()
    thread.join()


def test_loopback_and_read_capture_flow(service):
    bridge, server, info, runtime = service
    assert server.server_address[0] == "127.0.0.1"
    assert request(runtime, "status")["input_enabled"] is False
    assert request(runtime, "capture")["image_width"] == 1600
    assert request(runtime, "note", {"text": "Inspect the enemy tooltip."}) == {"updated": True}
    assert bridge.note == "Inspect the enemy tooltip."
    assert request(runtime, "stop")["input_enabled"] is False


@pytest.mark.parametrize("browser", [False, True])
def test_unauthorized_and_browser_requests_are_rejected(service, browser):
    _, server, info, _ = service
    headers = {"Authorization": "Bearer " + info["token"], "Origin": "https://example.com"} if browser else {}
    req = Request(f"http://127.0.0.1:{server.server_port}/capture", data=b"{}", headers=headers)
    with pytest.raises(HTTPError) as error:
        urlopen(req)
    assert error.value.code == 403


def test_cannot_arm_via_network(service):
    bridge, _, _, runtime = service
    with pytest.raises(BridgeError, match="Unknown operation"):
        request(runtime, "arm")
    assert not bridge.armed


def test_button_request_and_result_over_http(service, monkeypatch):
    bridge, _, _, runtime = service
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    deliveries = []
    SessionRequests(bridge, runtime, sender=lambda *args: deliveries.append(args))
    request(runtime, "connect", {"thread_id": "11111111-1111-4111-8111-111111111111"})
    item = request(runtime, "request", {"kind": "connection_test"})
    assert len(deliveries) == 1
    assert not item["allow_actions"]
    body = {"request_id": item["request_id"]}
    assert request(runtime, "claim", body)["status"] == "working"
    assert request(runtime, "finish", {**body, "text": "Connected."}) == {"completed": True}
    assert request(runtime, "status")["note"] == "Connected."
    assert bridge.frame is None
    assert not bridge.armed
    with pytest.raises(BridgeError, match="completed"):
        request(runtime, "claim", body)


def test_play_settings_and_history_over_http(service):
    bridge, _, _, runtime = service
    bridge.history = PlayHistory(runtime / "plays", runtime / "fake-game")
    bridge.output = bridge.history.directory() / "captures"
    bridge.settings = SettingsTracker(bridge.history)
    assert request(runtime, "saves") == {"saves": [], "loaded_save": "unknown"}
    request(runtime, "play", {"operation": "rename", "label": "Development"})
    request(runtime, "play", {"operation": "link", "name": "Manual save label"})
    profiles = request(runtime, "profiles", {"profile_id": "balanced", "overrides": {"target_fps": 75}, "note": "Dev override"})
    assert profiles["profiles"]["balanced"]["note"] == "Dev override"
    snapshot = request(runtime, "settings-snapshot")
    assert snapshot["profile"]["target_fps"] == 75
    frame = request(runtime, "capture")
    request(runtime, "settings-observe", {"frame_id": frame["frame_id"], "values": {"display_mode": "Borderless Window"}})
    settings = request(runtime, "settings")
    assert settings["observations"]["display_mode"]["value"] == "Borderless Window"
    assert settings["latest_snapshot"]["snapshot_id"] == frame["settings_snapshot_id"]
    history = request(runtime, "history", {"limit": 2})
    assert history["current"]["linked_save"]["name"] == "Manual save label"
    assert history["selected_session_id"] == frame["play_session_id"]
    assert [event["kind"] for event in history["events"]] == ["settings_observed", "capture"]
    assert not bridge.desktop.sent
    with pytest.raises(BridgeError, match="Invalid play session ID"):
        request(runtime, "history", {"session_id": "../outside"})
