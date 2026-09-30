#!/usr/bin/env python3
"""Obtain a Hybrid Console access token for Online Automation Hub via a service account.

Online Automation Hub (console.redhat.com) accepts the short-lived SSO Bearer JWT from
client_credentials. It does NOT mint the same long-lived "offline token" that the
Connect to Hub UI issues for human users (that is a cloud-services refresh token).

Usage:
  export CLIENT_ID=... CLIENT_SECRET=...
  # or place them in ./.env
  python3 get_hub_access_token.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
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


def get_sa_access_token(client_id: str, client_secret: str) -> dict:
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


def main() -> int:
    root = Path(__file__).resolve().parent
    file_env = load_dotenv(root / ".env")
    client_id = os.environ.get("CLIENT_ID") or file_env.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET") or file_env.get("CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Set CLIENT_ID and CLIENT_SECRET (env or .env)", file=sys.stderr)
        return 1

    try:
        token_resp = get_sa_access_token(client_id, client_secret)
    except urllib.error.HTTPError as e:
        print(e.read().decode(errors="replace"), file=sys.stderr)
        return 1

    access = token_resp.get("access_token")
    if not access:
        print(json.dumps(token_resp, indent=2), file=sys.stderr)
        return 1

    json.dump(
        {
            "access_token": access,
            "expires_in": token_resp.get("expires_in"),
            "token_type": token_resp.get("token_type"),
            "scope": token_resp.get("scope"),
            "notes": [
                "Short-lived SSO access token (typically 900s).",
                "Use as: Authorization: Bearer <access_token>",
                "Against: https://console.redhat.com/api/automation-hub/",
                "This is NOT the Connect-to-Hub offline refresh token.",
            ],
        },
        sys.stdout,
        indent=2,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
