"""Steady's small optional server: shared content and one administrator login.

Run `python server.py` from this directory. No third-party packages required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
_data_path = os.environ.get("STEADY_DATA_DIR")
DATA_DIR = Path(_data_path or ROOT).resolve()
if _data_path and not DATA_DIR.is_dir():
    raise RuntimeError(f"STEADY_DATA_DIR does not exist: {DATA_DIR}")
CONTENT_FILE = DATA_DIR / "content.json"
ADMIN_FILE = DATA_DIR / "admin.json"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/diagrams.css": ("diagrams.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
SESSIONS: dict[str, float] = {}
FAILED_LOGINS: dict[str, list[float]] = {}
MAX_BODY = 25 * 1024 * 1024
SESSION_LIFETIME = 12 * 60 * 60


def write_json_atomic(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        temp_name = file.name
    os.replace(temp_name, path)


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def password_hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000).hex()


def initialize_admin_from_env() -> None:
    """Provision the first admin through a deployment secret, if provided."""
    password = os.environ.pop("STEADY_ADMIN_PASSWORD", "")
    if ADMIN_FILE.exists() or not password:
        return
    if len(password) < 8:
        raise ValueError("STEADY_ADMIN_PASSWORD must have at least 8 characters")
    salt = secrets.token_bytes(16)
    write_json_atomic(ADMIN_FILE, {"salt": salt.hex(), "hash": password_hash(password, salt)})


class Handler(BaseHTTPRequestHandler):
    server_version = "Steady/1.0"

    def _send(self, status: int, payload: dict | None = None, *, cookie: str | None = None) -> None:
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; base-uri 'none'; form-action 'self'")
        if cookie is not None:
            secure = "; Secure" if os.environ.get("STEADY_HTTPS") == "1" else ""
            age = SESSION_LIFETIME if cookie else 0
            self.send_header("Set-Cookie", f"steady_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}{secure}")
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            parsed = urlsplit(origin)
            return parsed.netloc == self.headers.get("Host") and parsed.scheme in ("http", "https")
        except ValueError:
            return False

    def _body(self) -> dict | None:
        if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Send JSON."})
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > MAX_BODY:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Request is too large."})
                return None
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected object")
            return payload
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON."})
            return None

    def _session_token(self) -> str:
        for part in self.headers.get("Cookie", "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == "steady_session":
                return value
        return ""

    def _authenticated(self) -> bool:
        token = self._session_token()
        expiry = SESSIONS.get(token, 0)
        if expiry <= time.time():
            SESSIONS.pop(token, None)
            return False
        return True

    def _grant_session(self) -> None:
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = time.time() + SESSION_LIFETIME
        self._send(HTTPStatus.OK, {"authenticated": True}, cookie=token)

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._send(HTTPStatus.OK, {
                "configured": ADMIN_FILE.exists(),
                "authenticated": self._authenticated(),
                "storage": "server",
            })
            return
        if path == "/api/content":
            self._send(HTTPStatus.OK, {"content": read_json(CONTENT_FILE)})
            return
        static = STATIC_FILES.get(path)
        if not static:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        filename, content_type = static
        body = (ROOT / filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._same_origin():
            self._send(HTTPStatus.FORBIDDEN, {"error": "Invalid origin."})
            return
        if path == "/api/logout":
            SESSIONS.pop(self._session_token(), None)
            self._send(HTTPStatus.OK, {"authenticated": False}, cookie="")
            return
        if path == "/api/setup":
            if ADMIN_FILE.exists():
                self._send(HTTPStatus.CONFLICT, {"error": "Administrator already configured."})
                return
            host_header = urlsplit("//" + self.headers.get("Host", "")).hostname
            if self.client_address[0] not in ("127.0.0.1", "::1") or host_header not in ("127.0.0.1", "localhost", "::1"):
                self._send(HTTPStatus.FORBIDDEN, {"error": "Set up the administrator from the server computer."})
                return
            payload = self._body()
            if payload is None:
                return
            password = payload.get("password", "")
            if not isinstance(password, str) or len(password) < 8:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "Password needs at least 8 characters."})
                return
            salt = secrets.token_bytes(16)
            write_json_atomic(ADMIN_FILE, {"salt": salt.hex(), "hash": password_hash(password, salt)})
            self._grant_session()
            return
        if path == "/api/login":
            payload = self._body()
            if payload is None:
                return
            ip = self.client_address[0]
            now = time.time()
            recent = [stamp for stamp in FAILED_LOGINS.get(ip, []) if now - stamp < 900]
            if len(recent) >= 5:
                self._send(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many attempts. Try again in 15 minutes."})
                return
            record = read_json(ADMIN_FILE)
            password = payload.get("password", "")
            valid = False
            if record and isinstance(password, str):
                digest = password_hash(password, bytes.fromhex(record["salt"]))
                valid = hmac.compare_digest(digest, record["hash"])
            if not valid:
                recent.append(now)
                FAILED_LOGINS[ip] = recent
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "Incorrect password."})
                return
            FAILED_LOGINS.pop(ip, None)
            self._grant_session()
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_PUT(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/content":
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        if not self._same_origin() or not self._authenticated():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "Unlock the editor again."})
            return
        payload = self._body()
        if payload is None:
            return
        settings = payload.get("settings")
        scenarios = payload.get("scenarios")
        if not isinstance(settings, dict) or not isinstance(scenarios, list):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid content structure."})
            return
        ids = [item.get("id") for item in scenarios if isinstance(item, dict)]
        if len(ids) != len(scenarios) or not all(isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "Guide IDs must be unique."})
            return
        if not all(isinstance(item.get("title"), str) and isinstance(item.get("steps"), list)
                   and item["steps"] and all(isinstance(step, dict) and isinstance(step.get("title"), str)
                   and isinstance(step.get("body"), str) for step in item["steps"]) for item in scenarios):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid guide content."})
            return
        write_json_atomic(CONTENT_FILE, payload)
        self._send(HTTPStatus.OK, {"saved": True})


if __name__ == "__main__":
    initialize_admin_from_env()
    host = os.environ.get("STEADY_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("STEADY_PORT", "4173")))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Steady running at http://{host}:{port}/", flush=True)
    print("Create the administrator password from this computer before sharing the site.", flush=True)
    server.serve_forever()
