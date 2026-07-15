# demo-aap-survey-pem-key — AAP Password survey PEM private key reconstruction

Demonstrates how to paste a **multi-line PEM or OpenSSH private key** into Ansible Automation Platform's **Password** survey field (masked like a secret), then **reconstruct proper PEM line breaks** in the playbook before using the key in downstream tasks.

This demo is for **PEM-wrapped private keys only** — not arbitrary multi-line secrets (passwords, API tokens, config blobs, etc.).

## The problem

AAP **Password** survey fields are single-line in the UI. When a user pastes a multi-line private key, the controller **collapses newlines to spaces** before the value reaches your playbook:

```json
"survey_pem_key": "-----BEGIN OPENSSH PRIVATE KEY----- b3BlbnNzaC1rZXktdjEAAAAA... -----END OPENSSH PRIVATE KEY-----"
```

A debug task on the raw survey variable will show the same squashed shape — spaces where line breaks used to be. Downstream modules that expect a normal PEM file (`copy`, `community.crypto`, `command` with `stdin:`, etc.) will fail unless you rebuild the structure first.

## What this shows

The `aap_survey_pem_key` role:

| Step | Action |
| :--- | :--- |
| 1 | Read the squashed survey value via `lookup('vars', aap_survey_pem_key_var)` |
| 2 | Detect PEM type from the `-----BEGIN …-----` header |
| 3 | Strip headers, whitespace, and literal `\n` sequences from the base64 body |
| 4 | Re-wrap the body into 64-character lines and rebuild PEM headers |
| 5 | Optionally validate private key structure (`openssl pkey` for standard PEM, `ssh-keygen -y` for OpenSSH) |
| 6 | Expose `aap_survey_pem_key_reconstructed` for later tasks |

Sensitive steps use `no_log: true` so job output does not echo key material.

## File layout

```text
demo-aap-survey-pem-key/
├── playbook.yml              # CLI demo (simulates AAP squashing + reconstruction)
├── playbook-aap.yml          # AAP job template entry point
├── ansible.cfg
├── vars/
│   └── survey_pem_key.example.yml   # Example squashed value captured from AAP
└── roles/aap_survey_pem_key/
    ├── defaults/main.yml
    └── tasks/
        ├── main.yml          # resolve input, include subtasks
        ├── reconstruct.yml   # PEM line-break rebuild
        ├── validate.yml      # openssl / ssh-keygen checks
        └── report.yml        # safe summary (no key body)
```

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

**Requirements:** `openssl` and `ssh-keygen` on the machine running the playbook (controller / execution environment).

## AAP job template setup

1. Project/sync this repo (or copy just this demo directory).
2. Create a job template:
   - **Playbook:** `playbook-aap.yml`
   - **Inventory:** `localhost` (or any inventory with `localhost` in it)
   - **Credentials:** none required for the demo itself
   - **Execution environment:** must include `openssl` and `ssh-keygen` (default `ee-supported-rhel8` / platform EE images do)
3. Add a **Survey** question:

| Field | Value |
| :--- | :--- |
| **Question variable** | `survey_pem_key` |
| **Type** | **Password** |
| **Required** | Yes |
| **Description** | Paste your full multi-line private key (PEM or OpenSSH). Newlines are OK in the paste box — AAP will squash them; this playbook reconstructs them. |

4. Optional job template extra vars (or additional survey questions):

| Variable | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `aap_survey_pem_key_validate` | boolean | `true` | Set `false` to reconstruct only (skip `openssl` / `ssh-keygen` check) |
| `aap_survey_pem_key_var` | string | `survey_pem_key` | Change only if your survey question uses a different variable name |

### What to look for in AAP job output

**Before reconstruction** — if you debug the raw survey var, expect spaces instead of newlines inside the key body.

**After the role runs** — the report task prints safe metadata only:

- `detected_pem_type` — e.g. `OPENSSH PRIVATE KEY`
- `reconstructed_line_count` — should match a normal PEM file (typically 5–9 lines for Ed25519)
- `validation_rc: 0` — key structure is intact (when validation is enabled)

Use `aap_survey_pem_key_reconstructed` in later job template tasks.

### Example downstream task

```yaml
- name: Write reconstructed private key to target
  ansible.builtin.copy:
    content: "{{ aap_survey_pem_key_reconstructed }}"
    dest: /etc/ssh/deploy_key
    mode: "0600"
  no_log: true
```

## CLI demo vs. AAP usage

| Step | CLI (`playbook.yml`) | AAP (`playbook-aap.yml`) |
| :--- | :--- | :--- |
| **Simulate squashing** | Play 1 generates a temp Ed25519 key and collapses newlines to spaces | **Not needed** — AAP does this when the user submits the Password survey |
| **Reconstruct + validate** | Play 2 runs the `aap_survey_pem_key` role | Same role — survey provides `survey_pem_key` directly |
| **Prove downstream use** | Play 2 extracts the public key with `ssh-keygen -y` | Add your own tasks after `include_role` |

## Variables

Role defaults: `roles/aap_survey_pem_key/defaults/main.yml`.

### Survey / playbook input (not role-prefixed)

These come from the AAP survey or `-e` extra vars on the CLI:

| Variable | Purpose |
| :--- | :--- |
| `survey_pem_key` | Raw squashed PEM key from the Password survey answer |

### Role configuration (role-prefixed)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `aap_survey_pem_key_validate` | `true` | Run `openssl` / `ssh-keygen` integrity check |
| `aap_survey_pem_key_var` | `survey_pem_key` | Name of the extra var to read the squashed key from |

### Role facts (for downstream tasks)

| Fact | Purpose |
| :--- | :--- |
| `aap_survey_pem_key_reconstructed` | Multi-line PEM string ready for use |
| `aap_survey_pem_key_type` | Detected PEM header type (e.g. `OPENSSH PRIVATE KEY`) |
| `aap_survey_pem_key_validation_rc` | Exit code from validation (`0` = OK; omitted when validation is disabled) |

## Why Password survey type?

AAP **Password** survey fields mask input in the UI and treat the value as sensitive in job extra vars. That is preferable for private keys even though the field is single-line.

**Multiline Text** survey fields preserve newlines but are **not masked** — avoid those for private keys.

## Supported PEM types

| PEM header | Reconstruct? | Validate? |
| :--- | :--- | :--- |
| `OPENSSH PRIVATE KEY` | Yes | `ssh-keygen -y -f /dev/stdin` |
| `PRIVATE KEY`, `RSA PRIVATE KEY`, `EC PRIVATE KEY`, etc. | Yes | `openssl pkey -check -noout` |
| `CERTIFICATE`, `PUBLIC KEY` | Yes (re-wraps base64) | No — set `aap_survey_pem_key_validate: false` |

## Things to try

1. **CLI round trip** — `ansible-playbook playbook.yml` and confirm `validation_rc: 0` plus public-key extraction at the end.
2. **Captured AAP value** — copy squashed output from an AAP job into `vars/survey_pem_key.yml` and run with `demo_simulate_aap_squash=false`.
3. **Reconstruct only** — pass `-e aap_survey_pem_key_validate=false` to skip crypto validation (useful for PEM certificates).
4. **Custom survey name** — rename the survey question to e.g. `deploy_key` and set `aap_survey_pem_key_var=deploy_key` on the job template.
5. **Standard PEM key** — test with an RSA or EC key in PEM format (not OpenSSH wire format) and confirm `openssl pkey` validation path runs.

## Limitations

- **Private keys only** — not for arbitrary multi-line secrets without PEM `-----BEGIN …-----` / `-----END …-----` headers.
- Validation requires `openssl` and `ssh-keygen` on the execution environment / controller.
- AAP may fold YAML-style `>-` blocks in debug output; the role strips all whitespace from the base64 body before re-wrapping, so folded survey values still reconstruct correctly.
- PEM reconstruction is built with multiple short `set_fact` steps (not a YAML literal `|` block) so task indentation is not copied into PEM lines and ansible-lint line-length rules are satisfied.
- Always treat `aap_survey_pem_key_reconstructed` as sensitive — use `no_log: true` on tasks that handle it in production playbooks.

## Adapting for production

Copy the `roles/aap_survey_pem_key` role into your project (or add this repo as an AAP project source) and `include_role` it early in any job template that accepts a pasted private key via Password survey. Downstream tasks in the same play can reference `aap_survey_pem_key_reconstructed` directly.

## Related demos

- [demo-hosts-advanced](../demo-hosts-advanced/README.md) — normalizing messy **host limit** survey input (not secrets)
