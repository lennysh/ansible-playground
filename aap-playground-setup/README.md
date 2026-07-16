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
created. Credential secrets use `update_secrets: false` so re-runs do not wipe
values you filled in manually.

## Layout

```text
aap-playground-setup/
├── playbook.yml                 # dispatch entry point
├── collections/requirements.yml # infra.aap_configuration
├── docs/CLICKOPS_GUIDE.md       # manual seed steps
└── vars/                        # CaC definitions (edit these to extend)
```

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
