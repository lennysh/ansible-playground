# Demos

Self-contained playbooks — each directory has a `playbook.yml` (CLI) and, for
AAP-runnable samples, `playbook-aap.yml`. See the root
[README](../README.md) for bootstrap and pre-commit notes.

## Catalog

| Demo | Topic |
|------|-------|
| [strategy-free](strategy-free/README.md) | [`strategy: free`](strategy-free/README.md) — how the free execution strategy lets hosts run tasks independently instead of waiting at task barriers |
| [ansible-forks-async](ansible-forks-async/README.md) | [Forks and async jobs](ansible-forks-async/README.md) — how `forks` limits parallel host work and how `async` + `poll: 0` frees controller forks while remote jobs run |
| [hosts-advanced](hosts-advanced/README.md) | [Normalizing messy host limit input](hosts-advanced/README.md) — parsing AAP survey-style host lists into a clean dynamic `hosts:` target |
| [when](when/README.md) | [`when:` condition examples and pitfalls](when/README.md) — version checks, boolean coercion, `default()` bugs, and AND/OR grouping |
| [local-facts](local-facts/README.md) | [Local facts (`facts.d`)](local-facts/README.md) — default `/etc/ansible/facts.d` vs custom `fact_path`; `cat` before/after, re-gather with `setup`, scoped cleanup in `always` |
| [jinja2-filters](jinja2-filters/README.md) | [Jinja2 built-in filters](jinja2-filters/README.md) — runnable example of every stock Jinja2 filter (54 including aliases) |
| [ansible-filters](ansible-filters/README.md) | [ansible.builtin filters](ansible-filters/README.md) — runnable example of every ansible-core filter plugin (70 filters) |
| [lint-noqa](lint-noqa/README.md) | [Suppressing `yaml[line-length]`](lint-noqa/README.md) — `# noqa` vs yamllint for long lines |
| [dynamic-inventory-csv](dynamic-inventory-csv/README.md) | [CSV-driven dynamic inventory](dynamic-inventory-csv/README.md) — one plugin, many inventory YAML filters from a single spreadsheet |
| [dynamic-inventory-merge](dynamic-inventory-merge/README.md) | [Merging flat inventories via plugin](dynamic-inventory-merge/README.md) — layer INI/YAML/JSON sources with last-wins precedence |
| [dynamic-inventory](dynamic-inventory/README.md) | [AAP inventory source YAML catalog](dynamic-inventory/README.md) — copy-paste inventory plugin examples for AAP sources |
| [dynamic-inventory-with-static-vars](dynamic-inventory-with-static-vars/README.md) | [Dynamic inventory + static vars](dynamic-inventory-with-static-vars/README.md) — Proxmox plugin with `group_vars` / `host_vars` |
| [download-collection-tarball](download-collection-tarball/README.md) | [Download a collection tarball from Automation Hub](download-collection-tarball/README.md) — offline token → SSO → Hub API → S3 artifact; survey-friendly extra vars for AAP |
| [satellite-sync-and-promote](satellite-sync-and-promote/README.md) | [Satellite sync, wait, and lifecycle promote](satellite-sync-and-promote/README.md) — sync/publish/DEV, then tag-driven promote to QA and PROD after validation |
| [vmware-survey-options](vmware-survey-options/README.md) | [vSphere survey option gather](vmware-survey-options/README.md) — pull vsphere_destination / vsphere_datastore / vsphere_folder / vsphere_portgroup from vCenters and refresh an AAP provision JT survey |
| [kerberos-winrm](kerberos-winrm/README.md) | [Kerberos tickets for WinRM](kerberos-winrm/README.md) — EE diagnostics before/after `win_ping`; run via **ansible-navigator** or AAP only |
| [gmsa-winrm](gmsa-winrm/README.md) | [gMSA WinRM authentication](gmsa-winrm/README.md) — fetch `msDS-ManagedPassword` from AD, auth over WinRM as a gMSA; includes [lab-setup](gmsa-winrm/lab-setup/README.md) from scratch |
| [winrm-vs-psrp](winrm-vs-psrp/README.md) | [WinRM vs PSRP timing (Kerberos)](winrm-vs-psrp/README.md) — manual vs managed kinit, same Windows host, per-iteration comparison via Navigator/AAP EE |
| [aap-connectivity](aap-connectivity/README.md) | [AAP installer connectivity preflight](aap-connectivity/README.md) — Redis cluster bus, Receptor mesh, PostgreSQL, and platform TCP checks against an installer inventory |
| [aap-survey-pem-key](aap-survey-pem-key/README.md) | [AAP Password survey PEM keys](aap-survey-pem-key/README.md) — paste a masked multi-line private key into a Password survey; reconstruct PEM line breaks before downstream tasks |
| [support-assist](support-assist/README.md) | [infra.support_assist](support-assist/README.md) — AAP API gather, OCP must-gather, sosreport, and RH case create/update with surveyed AAP job templates |
| [aap-project-sync-collections](aap-project-sync-collections/README.md) | [Project sync collection inventory](aap-project-sync-collections/README.md) — parse galaxy install events from project updates (versions, download hosts, requirements/deps) across all or selected projects |
| [aap-pg-external-migrate](aap-pg-external-migrate/README.md) | [External→external Postgres migrate](aap-pg-external-migrate/README.md) — CLI playbook mirroring the controller operator `migrate_data.yml` dump\|restore pipe without requiring a managed PG pod (CLI-only) |
| [per-host-secrets](per-host-secrets/README.md) | [Per-host secrets preflight](per-host-secrets/README.md) — modular role that fetches each host's credentials from CyberArk, Vault, or Bitwarden before workload plays |
| [wjt-verbosity](wjt-verbosity/README.md) | [WJT survey verbosity override](wjt-verbosity/README.md) — workflow survey drives API updates to child job template verbosity, then resets for manual runs |

## Running a demo

```bash
cd demos/<name>
ansible-playbook playbook.yml
```

**Kerberos / Windows demos** ([kerberos-winrm](kerberos-winrm/README.md), [winrm-vs-psrp](winrm-vs-psrp/README.md), [gmsa-winrm](gmsa-winrm/README.md)) must run via **ansible-navigator** or **AAP** inside an execution environment — not bare `ansible-playbook` on your workstation (they template `/etc/krb5.conf` on the controller / in the EE).

**PEM key survey demo** ([aap-survey-pem-key](aap-survey-pem-key/README.md)) requires `openssl` and `ssh-keygen` on the controller / execution environment.

Each demo README includes details on what to look for in the output, things to try, and — where relevant — how to adapt the pattern for use in Ansible Automation Platform (AAP).
