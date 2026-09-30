# Online Automation Hub via Hybrid Console Service Accounts

Proof-of-concept: use a Red Hat Hybrid Cloud Console **service account**
(`CLIENT_ID` / `CLIENT_SECRET`) to authenticate to hosted Automation Hub on
`console.redhat.com` and download certified collections with `ansible-galaxy`.

> **Not official support.** Red Hat docs still say hosted Automation Hub does
> not support service-account auth for the Connect-to-Hub / offline-token flow.
> This repo shows what works empirically today via OAuth2 `client_credentials`.

## What works vs what does not

| Goal | Result |
|------|--------|
| Mint the same long-lived **offline token** as Connect to Hub → Load Token | **No** — that is a human `cloud-services` SSO refresh token |
| Call hosted Hub APIs with a service account | **Yes** — short-lived Bearer JWT (~900s, scope `api.console`) |
| Use that with `ansible-galaxy` | **Yes** — via the local auth shim (galaxy only knows `refresh_token`) |

Same SSO URL for both personal offline tokens and service accounts:

`https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token`

| Mode | Grant |
|------|-------|
| Personal offline token | `grant_type=refresh_token` + `client_id=cloud-services` + `refresh_token=…` |
| Service account | `grant_type=client_credentials` + `scope=api.console` + `client_id` + `client_secret` |

## Prerequisites

1. Create a [service account](https://console.redhat.com/iam/service-accounts) on the Hybrid Cloud Console.
2. Copy the client ID and client secret (shown once).
3. Add the service account to a User Access group with whatever Hub/content permissions your org requires.
4. Python 3, `curl`, and `ansible-galaxy` (from ansible-core) on your PATH.

## Quick start

```bash
cp .env.example .env
# edit .env — set CLIENT_ID and CLIENT_SECRET

set -a && source .env && set +a

# 1) Get a short-lived Hub access token
python3 get_hub_access_token.py

# 2) Or use ansible-galaxy via the local SSO shim
python3 galaxy_sa_auth_shim.py --port 8765   # leave running

# other terminal:
cp ansible.cfg.example ansible.cfg
ansible-galaxy collection download ansible.posix:2.2.2 -p ./cols
```

### Curl-only

```bash
set -a && source .env && set +a

ACCESS_TOKEN=$(curl -sS \
  https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d scope=api.console \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://console.redhat.com/api/automation-hub/v3/plugin/ansible/content/published/collections/index/?limit=1"
```

## Why the shim?

`ansible-galaxy` with `auth_url` always POSTs `grant_type=refresh_token`. Service accounts have no refresh token.

`galaxy_sa_auth_shim.py` listens on `http://127.0.0.1:8765/token`, ignores that body, and returns a real SA access token from SSO via `client_credentials`. Point `ansible.cfg` `auth_url` at the shim (see `ansible.cfg.example`).

Putting a SA JWT in `token=` **without** the shim fails: galaxy sends `Authorization: Token …` and the console gateway expects a Bearer JWT.

## Repo layout

| File | Purpose |
|------|---------|
| `.env.example` | Template for `CLIENT_ID` / `CLIENT_SECRET` |
| `get_hub_access_token.py` | Print SA access-token JSON |
| `galaxy_sa_auth_shim.py` | Local `auth_url` for ansible-galaxy |
| `ansible.cfg.example` | Galaxy servers → Hub published/validated + shim |

Do **not** commit `.env` or real secrets.

## Notes

- Access tokens expire in ~15 minutes; the shim refreshes on each galaxy auth call.
- Official AAP Org Galaxy credentials still expect `url` + `auth_url` + offline `token`. Native SA support would need ansible-core `KeycloakToken` to learn `client_credentials`, plus awx-plugins / controller wiring.
- Artifact downloads redirect to S3 pre-signed URLs — do not forward `Authorization` on the redirect (ansible-galaxy handles this).
