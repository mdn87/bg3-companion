from pathlib import Path

import pytest

from bg3_helper.core import Bridge, BridgeError
from bg3_helper.history import PlayHistory, discover_saves, read_json, write_json
from bg3_helper.session import SessionRequests
from bg3_helper.settings import SettingsTracker
from test_core import Desktop, proposal


@pytest.fixture
def tracked(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    history = PlayHistory(tmp_path / "plays", tmp_path / "game")
    desktop = Desktop()
    bridge = Bridge(desktop, tmp_path / "unused", history=history)
    bridge.settings = SettingsTracker(history, inspect_system=lambda: {"gpus": [{"name": "Test GPU"}]})
    deliveries = []
    session = SessionRequests(bridge, tmp_path / "runtime", sender=lambda *args: deliveries.append(args))
    session.connect("11111111-1111-4111-8111-111111111111")
    return bridge, history, session, deliveries


def save_file(history, name="Campaign/Quicksave.lsv"):
    path = history.game_data / "PlayerProfiles" / "Public" / "Savegames" / "Story" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"Opaque save contents are never parsed by the companion")
    return path


def test_save_links_are_explicit_and_keep_the_selected_revision(tracked):
    _, history, _, _ = tracked
    path = save_file(history)
    save_file(history, "Direct.lsv")
    saves = discover_saves(history.game_data)
    assert {item["name"] for item in saves} == {"Quicksave", "Direct"}
    assert history.status()["linked_save"] is None
    selected = next(item for item in saves if item["name"] == "Quicksave")
    history.link_save(save_id=selected["save_id"], note="Selected before dev test")
    path.write_bytes(b"New save revision")
    new_version = next(item for item in discover_saves(history.game_data) if item["save_id"] == selected["save_id"])
    assert new_version["revision"] != selected["revision"]
    assert history.status()["linked_save"]["revision"] == selected["revision"]
    assert history.status()["linked_save"]["association"] == "selected_file_metadata"
    assert path.read_bytes() == b"New save revision"
    with pytest.raises(BridgeError, match="no longer available"):
        history.link_save(save_id="missing-save")


def test_sessions_resume_after_restart_with_capture_context_intact(tracked):
    bridge, history, _, _ = tracked
    first = history.status()["play_session_id"]
    history.rename("4070pc development")
    history.link_save(name="Before the grove", note="Manual label until a save is selected")
    frame = bridge.capture()
    bridge.arm()
    second = bridge.play("new", label="Another campaign")
    assert second["play_session_id"] != first
    assert second["linked_save"] is None
    assert not bridge.armed and bridge.frame is None and bridge.used
    assert bridge.output.parent.name == second["play_session_id"]
    bridge.play("resume", session_id=first)
    reopened = PlayHistory(history.root, history.game_data)
    assert reopened.status()["label"] == "4070pc development"
    assert reopened.status()["linked_save"]["name"] == "Before the grove"
    assert read_json(Path(frame["full_path"]).with_suffix(".json"))["linked_save"]["name"] == "Before the grove"
    assert reopened.events(limit=1)[0]["data"]["frame_id"] == frame["frame_id"]
    public = reopened.status()
    public["linked_save"]["name"] = "Unrelated edit"
    assert reopened.status()["linked_save"]["name"] == "Before the grove"


@pytest.mark.parametrize("session_id", ["../outside", "C:/outside", "20260905-123456-../bad"])
def test_history_rejects_paths_outside_its_sessions(tracked, session_id):
    _, history, _, _ = tracked
    with pytest.raises(BridgeError, match="Invalid play session ID"):
        history.events(session_id)


def test_legacy_import_copies_evidence_once_without_changing_originals(tracked, tmp_path):
    _, history, _, _ = tracked
    legacy = Bridge(Desktop(), tmp_path / "legacy")
    original = legacy.capture()
    source = legacy.output / (original["frame_id"] + ".json")
    content = source.read_bytes()
    assert history.import_legacy(legacy.output) == 1
    assert history.import_legacy(legacy.output) == 0
    assert source.read_bytes() == content
    imported = read_json(history.directory() / "captures" / source.name)
    assert imported["reason"] == "legacy_import"
    assert imported["linked_save"] is None
    assert imported["request_id"] is None
    assert Path(imported["full_path"]).read_bytes() == Path(original["full_path"]).read_bytes()
    assert Path(imported["full_path"]).parent == history.directory() / "captures"


def test_legacy_import_rejects_external_image_references(tracked, tmp_path):
    _, history, _, _ = tracked
    source = tmp_path / "legacy"
    source.mkdir()
    external = tmp_path / "outside.png"
    external.write_bytes(b"Not part of legacy captures")
    frame_id = "a" * 32
    write_json(source / (frame_id + ".json"), {"frame_id": frame_id, "full_path": str(external)})
    with pytest.raises(BridgeError, match="unexpected image"):
        history.import_legacy(source)
    assert not (history.root / "legacy-import.json").exists()


def test_settings_baseline_copies_config_and_does_not_guess_render_enums(tracked):
    bridge, history, _, _ = tracked
    source = history.game_data / "graphicSettings.lsx"
    source.parent.mkdir(parents=True)
    content = b'''<save><node id="ConfigEntry"><attribute id="MapKey" value="ScreenWidth"/><attribute id="Value" value="2560"/></node>
    <node id="ConfigEntry"><attribute id="MapKey" value="ScreenHeight"/><attribute id="Value" value="1440"/></node>
    <node id="ConfigEntry"><attribute id="MapKey" value="ResolutionUpscaleMode"/><attribute id="Value" value="17"/></node></save>'''
    source.write_bytes(content)
    result = bridge.settings.snapshot(request_id="b" * 32)
    assert result["configured_resolution"] == "2560 x 1440"
    assert result["graphics_raw"]["ResolutionUpscaleMode"] == "17"
    assert result["request_id"] == "b" * 32
    assert result["settings_snapshot_id"] == result["snapshot_id"]
    assert result["performance"] == {"measured": False, "fps": None}
    assert result["system"]["gpus"][0]["name"] == "Test GPU"
    assert Path(result["sources"][0]["snapshot_path"]).read_bytes() == content
    assert source.read_bytes() == content
    assert SettingsTracker(history).current()["latest_snapshot"] == result


def test_missing_game_files_still_allow_a_development_baseline(tracked):
    bridge, _, _, _ = tracked
    result = bridge.settings.snapshot()
    assert result["configured_resolution"] is None
    assert result["sources"] == []
    assert result["warnings"]
    assert result["profile"]["profile_id"] == "balanced"


def test_profiles_persist_only_overrides_and_keep_notes(tracked):
    bridge, history, _, _ = tracked
    settings = bridge.settings
    initial = settings.profiles()
    assert initial["active"] == "balanced"
    assert set(initial["profiles"]) == {"balanced", "performance", "quality"}
    settings.select_profile("balanced", {"target_fps": 75, "resolution": "Keep current"}, "Testing a 75 FPS cap")
    settings.select_profile("quality")
    restored = SettingsTracker(history).select_profile("balanced")
    profile = restored["profiles"]["balanced"]
    assert profile["overrides"] == {"target_fps": 75}
    assert profile["note"] == "Testing a 75 FPS cap"
    assert profile["revision"] == 1
    assert profile["stage"] == "starter_not_benchmarked"
    settings.select_profile("balanced", {}, "Back to starter defaults")
    assert settings.profiles()["profiles"]["balanced"]["target_fps"] == 60


@pytest.mark.parametrize("overrides", [{"target_fps": True}, {"target_fps": 0}, {"resolution": "Bogus"},
                                        {"upscaling": "17"}, {"background_audio": "yes"}, {"driver": "latest"}])
def test_invalid_profile_overrides_are_rejected_without_saving(tracked, overrides):
    bridge, _, _, _ = tracked
    before = bridge.settings.profiles()
    with pytest.raises(BridgeError):
        bridge.settings.select_profile("balanced", overrides)
    assert bridge.settings.profiles() == before


def test_observations_link_frames_and_record_actual_before_after_values(tracked):
    bridge, history, session, _ = tracked
    item = session.submit("setup")
    frame = item["frame"]
    first = bridge.settings.observe(frame["frame_id"], {"mute_sound_when_inactive": True}, "Before setup")
    assert first["changes"]["mute_sound_when_inactive"] == {"before": None, "after": True}
    next_frame = bridge.capture()
    changed = bridge.settings.observe(next_frame["frame_id"], {"mute_sound_when_inactive": False}, "Verified afterward")
    assert changed["request_id"] == item["request_id"]
    assert changed["changes"]["mute_sound_when_inactive"] == {"before": True, "after": False}
    assert bridge.settings.observations()["mute_sound_when_inactive"]["captured_at"] == next_frame["captured_at"]
    session.finish(item["request_id"], "Advice only test completed.")
    bridge.play("new", label="Separate test")
    with pytest.raises(BridgeError, match="does not belong"):
        bridge.settings.observe(frame["frame_id"], {"mute_sound_when_inactive": False})
    assert bridge.settings.observations() == {}


def test_smart_capture_actions_and_result_share_one_request_history(tracked):
    bridge, history, session, deliveries = tracked
    bridge.arm()
    item = session.submit("smart", "Inspect inventory")
    assert item["frame"]["reason"] == "smart_start"
    assert item["frame"]["request_id"] == item["request_id"]
    assert Path(deliveries[0][2]).is_relative_to(history.directory())
    session.claim(item["request_id"])
    action = proposal(bridge, smart_request_id=item["request_id"])
    result = bridge.act(action)
    assert result["after"]["request_id"] == item["request_id"]
    assert bridge.act(action) == result
    session.finish(item["request_id"], "Test result")
    events = history.events()
    assert sum(event["kind"] == "action_result" for event in events) == 1
    saved = read_json(history.directory() / "requests" / (item["request_id"] + ".result.json"))
    assert saved["status"] == "completed" and saved["result"] == "Test result"


def test_setup_freezes_profile_and_caps_actions_at_twelve(tracked, monkeypatch):
    bridge, history, session, _ = tracked
    monkeypatch.setattr("bg3_helper.core.time.sleep", lambda _seconds: None)
    bridge.arm()
    item = session.submit("setup")
    assert item["setup"]["request_id"] == item["request_id"]
    assert item["frame"]["settings_snapshot_id"] == item["setup"]["snapshot_id"]
    bridge.settings.select_profile("balanced", {"target_fps": 90}, "For the next setup request")
    claimed = session.claim(item["request_id"])
    assert claimed["setup"]["profile"]["target_fps"] == 60
    claimed["setup"]["profile"]["target_fps"] = 200
    assert session.status()["request"]["setup"]["profile"]["target_fps"] == 60
    for number in range(12):
        bridge.act(proposal(bridge, request_id=f"setup-{number}", smart_request_id=item["request_id"]))
    with pytest.raises(BridgeError, match="twelve gestures"):
        bridge.act(proposal(bridge, request_id="over-budget", smart_request_id=item["request_id"]))
    assert len(bridge.desktop.sent) == 12


def test_setup_advice_cannot_be_upgraded_and_session_switch_requires_stop(tracked):
    bridge, history, session, _ = tracked
    item = session.submit("setup")
    bridge.arm()
    with pytest.raises(BridgeError, match="advice only"):
        bridge.act(proposal(bridge, smart_request_id=item["request_id"]))
    for operation, values in (("new", {"label": "Next"}), ("link", {"name": "Another save"})):
        with pytest.raises(BridgeError, match="STOP"):
            bridge.play(operation, **values)
    bridge.stop()
    old_directory = history.directory()
    bridge.play("new", label="After STOP")
    assert session.current is None and not bridge.armed
    result = read_json(old_directory / "requests" / (item["request_id"] + ".result.json"))
    assert result["status"] == "cancelled"
    assert bridge.desktop.sent == []


@pytest.mark.parametrize("terminal", ["completed", "cancelled"])
def test_late_delivery_error_preserves_callback_or_stop_result(tracked, terminal):
    _, history, session, _ = tracked
    def sender(*_args):
        if terminal == "completed":
            session.finish(session.current["request_id"], "Already received")
        else:
            session.bridge.stop()
        raise BridgeError("Transport response lost")
    session.sender = sender
    with pytest.raises(BridgeError, match="response lost"):
        session.submit("connection_test")
    assert session.status()["request"]["status"] == terminal
    assert not list((history.directory() / "captures").glob("*.png"))
