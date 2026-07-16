# CaC examples (in-repo)

Canonical samples for Ansible Automation Platform Config-as-Code live under
[`vars/`](../vars/). Copy and extend these files when adding demos — do not
reach outside this repository for patterns.

Seed / clickops steps (org Galaxy credential, project, Setup JT):
**[CLICKOPS_GUIDE.md](CLICKOPS_GUIDE.md)**

## Object → sample file

| Object type | Variable key | Sample file | Notes |
|-------------|--------------|-------------|-------|
| Naming / SCM constants | *(facts)* | [`vars/bootstrap.yml`](../vars/bootstrap.yml) | Org name, project URL, credential/EE names |
| Organization | `aap_organizations` | [`vars/organizations.yml`](../vars/organizations.yml) | |
| Inventory | `controller_inventories` | [`vars/inventories.yml`](../vars/inventories.yml) | Localhost + Windows stub |
| Host | `controller_hosts` | [`vars/hosts.yml`](../vars/hosts.yml) | `ansible_connection: local` |
| Project | `controller_projects` | [`vars/projects.yml`](../vars/projects.yml) | `scm_update_on_launch: true` |
| Credential type | `controller_credential_types` | [`vars/credential_types.yml`](../vars/credential_types.yml) | Offline token + Satellite; `!unsafe` injectors |
| Credential | `controller_credentials` | [`vars/credentials.yml`](../vars/credentials.yml) | Placeholders with `update_secrets: false` |
| Execution environment | `controller_execution_environments` | [`vars/execution_environments.yml`](../vars/execution_environments.yml) | Kerberos / WinRM images |
| Job template + survey | `controller_templates` | [`vars/job_templates.yml`](../vars/job_templates.yml) | Setup JT + all `Demo \| …` surveys |

## Survey patterns in `job_templates.yml`

| Pattern | Example JT |
|---------|------------|
| Password (masked secret) | `Demo \| AAP Survey PEM Key` → `survey_pem_key` |
| Textarea | `Demo \| Hosts Advanced` → `host_limit` |
| Multiple choice / true-false | `Demo \| When`, Kerberos demos |
| Multiselect | `Demo \| AAP Connectivity` → suites |
| Integer defaults | `Demo \| Forks and Async` — use YAML ints (`12`, not `"12"`) |
| No survey | `Demo \| Ansible Filters`, `Demo \| Strategy Free` |
| Custom EE + ask inventory | `Demo \| Kerberos WinRM`, `Demo \| WinRM vs PSRP` |
| Custom credential on JT | Download Collection (Offline Token), Satellite |

## Adding a new AAP demo

1. Add `demo-<name>/playbook-aap.yml` (+ README survey docs).
2. Append a `Demo | …` entry to `vars/job_templates.yml` (copy the closest pattern above).
3. Extend credentials / EEs / inventories only if the demo needs new object types.
4. Re-run **Playground | Apply CaC** after project sync.
