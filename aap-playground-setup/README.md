# AAP Playground Setup

Config-as-Code bootstrap for **Lenny's Ansible Playground**. Creates (and later
updates) the AAP organization objects and surveyed job templates needed to run
the demos in this repository.

## First-time setup

Follow the clickops guide to create the seed objects, then launch the Setup job
template once:

→ **[docs/CLICKOPS_GUIDE.md](docs/CLICKOPS_GUIDE.md)**

## Re-run anytime

After you add a new demo (or change surveys / JT definitions under `vars/`),
sync the project and launch:

**Templates → `Playground | Apply CaC` → Launch**

The playbook is idempotent: existing objects are updated; missing ones are
created. Playground credentials use `state: exists` so re-runs do **not**
overwrite username, host, or secrets you set in the UI after first create.

## Layout

```text
aap-playground-setup/
├── playbook.yml                 # dispatch entry point
├── collections/requirements.yml # infra.aap_configuration
├── extra_vars.example.yml       # optional CLI overrides (Satellite, token, EE, …)
├── docs/
│   ├── CLICKOPS_GUIDE.md        # manual seed steps
│   └── CAC_EXAMPLES.md          # in-repo CaC sample index (copy from vars/)
└── vars/                        # CaC definitions — canonical examples per object type
```

When adding or changing demos, extend `vars/` using the patterns catalogued in
**[docs/CAC_EXAMPLES.md](docs/CAC_EXAMPLES.md)**.

## CLI alternative

With collections installed and AAP reachable:

```bash
export AAP_HOSTNAME=https://aap.example.com
export AAP_USERNAME=admin
export AAP_PASSWORD='...'
# or: export AAP_TOKEN='...'

ansible-galaxy collection install -r aap-playground-setup/collections/requirements.yml
ansible-playbook aap-playground-setup/playbook.yml
```

Optional credential / EE overrides (**initial create only** — credentials use
`state: exists`; see [`extra_vars.example.yml`](extra_vars.example.yml)):

| Extra var | Used for |
|-----------|----------|
| `playground_demos` | List of `Demo \| …` JT names (`[]` / omit = Setup JT only) |
| `playground_apply_all_demos` | `true` → apply every demo (CLI convenience) |
| `playground_machine_username` | Machine credential username |
| `playground_satellite_url` | Satellite credential host |
| `playground_satellite_username` | Satellite credential username |
| `playground_satellite_password` | Satellite credential password |
| `playground_offline_token` | Hub / offline-token credential |
| `playground_ee_registry` | Registry prefix for Kerberos / WinRM EE images |

```bash
cp aap-playground-setup/extra_vars.example.yml /tmp/playground-cac-extra.yml
# edit /tmp/playground-cac-extra.yml — do not commit secrets
ansible-playbook aap-playground-setup/playbook.yml -e @/tmp/playground-cac-extra.yml
```

First-time UI setup is two launches: **6a** (no survey yet) refreshes the Setup
JT and shared objects without demos; **6b** uses the new multiselect to pick
demos (default all). See [CLICKOPS_GUIDE.md](docs/CLICKOPS_GUIDE.md). Credential
shells use `state: exists` so later runs do not overwrite UI edits.

## What gets created

| Object | Notes |
|--------|-------|
| Organization | `Lenny's Ansible Playground` |
| Project | This git repo |
| Inventories | `Playground Inventory` (localhost) + `Playground Windows Inventory` (empty stub) |
| Credentials | AAP, Machine, Satellite, Hub Offline Token (placeholders) |
| Credential type | `Red Hat Offline Token`, `Red Hat Satellite Server` |
| Execution environments | Kerberos WinRM + WinRM vs PSRP images |
| Job templates | Setup JT + one JT per `playbook-aap.yml` demo with surveys |

Dynamic-inventory demos, `demo-lint-noqa`, and unfinished stubs are not given
job templates.
