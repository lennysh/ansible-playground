#!/usr/bin/env python3
"""Local auth shim so ansible-galaxy can use a Hybrid Console service account.

ansible-galaxy's KeycloakToken always POSTs:
  grant_type=refresh_token&client_id=cloud-services&refresh_token=<token>

Service accounts only support client_credentials (no offline refresh token).
This tiny HTTP server accepts ansible-galaxy's refresh_token form POST and
returns a real SA access_token from Red Hat SSO via client_credentials.

Example:
  export CLIENT_ID=... CLIENT_SECRET=...
  python3 galaxy_sa_auth_shim.py --port 8765 &
  # ansible.cfg:
  #   [galaxy_server.rh_hub]
  #   url=https://console.redhat.com/api/automation-hub/content/published/
  #   auth_url=http://127.0.0.1:8765/token
  #   token=ignored-placeholder
  ansible-galaxy collection download ansible.posix -p /tmp/cols
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SSO_TOKEN_URL = (
    "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
)


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def fetch_sa_token(client_id: str, client_secret: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "scope": "api.console",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()
    req = urllib.request.Request(
        SSO_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--env-file", default=str(Path(__file__).with_name(".env")))
    args = parser.parse_args()

    file_env = load_dotenv(Path(args.env_file))
    client_id = os.environ.get("CLIENT_ID") or file_env.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET") or file_env.get("CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("CLIENT_ID/CLIENT_SECRET required")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *a) -> None:
            print(f"[shim] {self.address_string()} {fmt % a}")

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode() if length else ""
            # ansible-galaxy body is ignored; we always use client_credentials
            _ = urllib.parse.parse_qs(raw)
            try:
                token = fetch_sa_token(client_id, client_secret)
            except Exception as e:  # noqa: BLE001
                body = json.dumps({"error": "server_error", "error_description": str(e)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps(
                {
                    "access_token": token["access_token"],
                    "expires_in": token.get("expires_in", 900),
                    "token_type": "Bearer",
                    "scope": token.get("scope", "api.console"),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            body = b'{"status":"ok","hint":"POST grant_type=refresh_token (ignored) to /token"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Listening on http://{args.host}:{args.port}/token")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
