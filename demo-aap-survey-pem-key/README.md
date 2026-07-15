# AAP Password survey — PEM private key reconstruction

Demonstrates how to paste a **multi-line PEM or OpenSSH private key** into Ansible Automation Platform's **Password** survey field (masked like a secret), then **reconstruct proper PEM line breaks** in the playbook before using the key in downstream tasks.

This demo is for **PEM-wrapped private keys only** — not arbitrary multi-line secrets (passwords, API tokens, config blobs, etc.).

AAP survey Password fields are single-line in the UI. When a user pastes a multi-line private key, the controller **collapses newlines to spaces** before the value reaches your playbook:

```json
"survey_pem_key": "-----BEGIN OPENSSH PRIVATE KEY----- b3BlbnNzaC1rZXktdjEAAAAA... -----END OPENSSH PRIVATE KEY-----"
```

This demo shows the Jinja2 reconstruction pipeline and optional validation with `openssl` or `ssh-keygen`.

## What it does

| Step | Action |
| :--- | :--- |
| 1 | Read the squashed survey value (`survey_pem_key`) |
| 2 | Detect PEM type from the `-----BEGIN …-----` header |
| 3 | Strip headers, whitespace, and literal `\n` sequences from the base64 body |
| 4 | Re-wrap the body into 64-character lines and rebuild PEM headers |
| 5 | Validate private key structure (`openssl pkey` for standard PEM, `ssh-keygen -y` for OpenSSH) |
| 6 | Expose `aap_survey_pem_key_reconstructed` for later tasks |

## Quick start (CLI)

Self-contained round trip — generates an ephemeral Ed25519 key, squashes it like AAP, then reconstructs and validates:

```bash
cd demo-aap-survey-pem-key
ansible-playbook playbook.yml
```

Test with a squashed value captured from AAP:

```bash
cp vars/survey_pem_key.example.yml vars/survey_pem_key.yml
# paste your squashed survey output into survey_pem_key
ansible-playbook playbook.yml -e @vars/survey_pem_key.yml \
  -e demo_simulate_aap_squash=false
```

## AAP job template

1. Project/sync this repo (or just this demo directory).
2. Create a job template using **`playbook-aap.yml`**.
3. Add a **Survey** question:

| Field | Value |
| :--- | :--- |
| **Question** | `survey_pem_key` |
| **Type** | **Password** |
| **Required** | Yes |
| **Description** | Paste your full multi-line private key (PEM or OpenSSH). Newlines are OK in the paste box — AAP will squash them; this playbook reconstructs them. |

4. Optional survey / extra vars:

| Variable | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `aap_survey_pem_key_validate` | boolean | `true` | Set `false` to reconstruct only (skip openssl/ssh-keygen check) |

### What to look for in AAP output

Before reconstruction, a debug of the raw survey var shows **spaces instead of newlines** inside the key body. After the role runs, the report task shows:

- `detected_pem_type` — e.g. `OPENSSH PRIVATE KEY`
- `reconstructed_line_count` — should match a normal PEM file (typically 5+ lines)
- `validation_rc: 0` — key structure is intact

Use `aap_survey_pem_key_reconstructed` in later job template tasks — for example `ansible.builtin.copy` with `content:`, `community.crypto` modules, or `command`/`shell` with `stdin:`.

## CLI demo vs. AAP usage

| Step | CLI (`playbook.yml`) | AAP (`playbook-aap.yml`) |
| :--- | :--- | :--- |
| **Simulate squashing** | Play 1 generates a temp key and collapses newlines to spaces | **Not needed** — AAP does this when the user submits the Password survey |
| **Reconstruct + validate** | Play 2 runs the `aap_survey_pem_key` role | Same role — survey provides `survey_pem_key` directly |

## Variables

See `roles/aap_survey_pem_key/defaults/main.yml`.

| Variable | Purpose |
| :--- | :--- |
| `survey_pem_key` | Raw squashed PEM key from the Password survey (extra var / survey answer) |
| `aap_survey_pem_key_validate` | Run openssl/ssh-keygen integrity check (default `true`) |
| `aap_survey_pem_key_var` | Extra-var name to read (default `survey_pem_key`) |

### Role facts (for downstream tasks)

| Fact | Purpose |
| :--- | :--- |
| `aap_survey_pem_key_reconstructed` | Multi-line PEM string ready for use |
| `aap_survey_pem_key_type` | Detected PEM header type |
| `aap_survey_pem_key_validation_rc` | Exit code from validation (when enabled) |

Sensitive tasks use `no_log: true` so job output does not echo key material.

## Why Password survey type?

AAP **Password** survey fields mask input in the UI and job extra vars (similar to credential fields). That is preferable for private keys even though the field is single-line. **Multiline Text** survey fields preserve newlines but are not masked — avoid those for keys.

## Supported PEM types

| PEM header | Reconstruct? | Validate? |
| :--- | :--- | :--- |
| `OPENSSH PRIVATE KEY` | Yes | `ssh-keygen -y` |
| `PRIVATE KEY`, `RSA PRIVATE KEY`, `EC PRIVATE KEY`, etc. | Yes | `openssl pkey -check` |
| `CERTIFICATE`, `PUBLIC KEY` | Yes (re-wraps base64) | No — set `aap_survey_pem_key_validate: false` |

## Limitations

- **Private keys only** — not for arbitrary multi-line secrets without PEM headers.
- Validation requires `openssl` and `ssh-keygen` on the execution environment / controller.
- AAP may also fold YAML-style `>-` blocks in debug output; the role strips all whitespace from the base64 body before re-wrapping, so folded survey values still reconstruct correctly.
- Build the reconstructed string in a **single Jinja expression** (not a YAML literal `|` block) so task indentation is not copied into PEM lines.
- Always treat `aap_survey_pem_key_reconstructed` as sensitive — use `no_log` on tasks that handle it in production playbooks.

## Related pattern

For normalizing messy **host limit** survey input (not secrets), see [demo-hosts-advanced](../demo-hosts-advanced/README.md).
