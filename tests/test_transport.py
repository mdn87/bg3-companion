import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from bg3_helper.transport import create_server, request
from bg3_helper.core import Bridge, BridgeError
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
