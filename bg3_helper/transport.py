"""Authenticated loopback bridge. CLI reads the local capability without printing it."""
import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .core import BridgeError
from .history import discover_saves


def create_server(bridge):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            auth = self.headers.get("Authorization", "")
            if self.headers.get("Origin") or not hmac.compare_digest(auth, "Bearer " + token):
                self.reply(403, {"error": "Local bridge authentication required; browser requests are not accepted."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 16384:
                    raise BridgeError("Request body is too large.")
                self.connection.settimeout(5)
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise BridgeError("Request body must be an object.")
                if self.path == "/status":
                    result = bridge.status()
                elif self.path == "/capture":
                    result = bridge.capture()
                elif self.path == "/crop":
                    result = bridge.crop(body.get("x"), body.get("y"), body.get("width"), body.get("height"))
                elif self.path == "/action":
                    result = bridge.act(body)
                elif self.path == "/stop":
                    bridge.stop()
                    result = {"input_enabled": False}
                elif self.path in {"/play", "/history", "/saves"}:
                    if bridge.history is None:
                        raise BridgeError("Play history is not configured in this bridge.")
                    with bridge.lock:
                        if self.path == "/play":
                            values = dict(body)
                            operation = values.pop("operation", None)
                            result = bridge.play(operation, **values)
                        elif self.path == "/saves":
                            result = {"saves": discover_saves(bridge.history.game_data), "loaded_save": "unknown"}
                        else:
                            result = {"current": bridge.history.status(), "sessions": bridge.history.sessions(),
                                      "directory": str(bridge.history.directory(body.get("session_id"))),
                                      "selected_session_id": body.get("session_id") or bridge.history.current["play_session_id"],
                                      "events": bridge.history.events(body.get("session_id"), body.get("limit", 500))}
                elif self.path in {"/profiles", "/settings-snapshot", "/settings-observe", "/settings"}:
                    if bridge.settings is None:
                        raise BridgeError("Settings tracking is not configured in this bridge.")
                    with bridge.lock:
                        if self.path == "/profiles":
                            result = (bridge.settings.select_profile(body["profile_id"], body.get("overrides"), body.get("note", ""))
                                      if "profile_id" in body else bridge.settings.profiles())
                        elif self.path == "/settings-snapshot":
                            status = bridge.status()
                            active = (status.get("session") or {}).get("request")
                            request_id = (active["request_id"] if active and active["status"] in
                                          {"sending", "queued", "working"} else None)
                            result = bridge.settings.snapshot(target=status["target"], request_id=request_id)
                        elif self.path == "/settings-observe":
                            result = bridge.settings.observe(body.get("frame_id"), body.get("values"), body.get("note", ""))
                        else:
                            result = bridge.settings.current()
                elif self.path in {"/connect", "/request", "/claim", "/finish"}:
                    if bridge.session is None:
                        raise BridgeError("Session buttons are not connected in this bridge.")
                    if self.path == "/connect":
                        result = bridge.session.connect(body.get("thread_id"))
                    elif self.path == "/request":
                        result = bridge.session.submit(body.get("kind"), body.get("objective", ""))
                    elif self.path == "/claim":
                        result = bridge.session.claim(body.get("request_id"))
                    else:
                        result = bridge.session.finish(body.get("request_id"), body.get("text"))
                elif self.path == "/note":
                    note = body.get("text")
                    if not isinstance(note, str) or len(note) > 6000:
                        raise BridgeError("Note must be text of at most 6000 characters.")
                    with bridge.lock:
                        bridge.note = note
                    result = {"updated": True}
                else:
                    self.reply(404, {"error": "Unknown operation."})
                    return
                if self.path != "/status":
                    bridge.last_error = result.get("error", "") if result.get("status") == "outcome_unknown" else ""
                self.reply(200, result)
            except (BridgeError, ValueError, TypeError) as exc:
                bridge.last_error = str(exc)
                self.reply(409, {"error": str(exc)})
            except Exception as exc:
                bridge.last_error = f"{type(exc).__name__}: {exc}"
                self.reply(500, {"error": bridge.last_error})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    descriptor = {"port": server.server_port, "token": token}
    return server, descriptor


def request(runtime: Path, operation: str, body=None):
    try:
        info = json.loads((runtime / "connection.json").read_text(encoding="utf-8"))
        port = info["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise BridgeError("Invalid local bridge port.")
        req = Request(f"http://127.0.0.1:{port}/{operation}",
                      data=json.dumps(body or {}).encode(),
                      headers={"Authorization": "Bearer " + info["token"], "Content-Type": "application/json"})
        with urlopen(req, timeout=45 if operation == "request" else 15) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            error = json.load(exc).get("error", "Bridge rejected the request.")
        except Exception:
            error = "Bridge rejected the request."
        raise BridgeError(error) from None
    except (OSError, URLError, KeyError, ValueError):
        raise BridgeError("Companion is not running. Start launch.cmd, then retry.") from None
