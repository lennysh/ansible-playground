# Ansible Demo Playground

Self-contained Ansible playbooks that demonstrate specific concepts, patterns, and pitfalls. Each demo lives in its own directory with a playbook and README explaining what it shows.

## AAP bootstrap

To load these demos into Ansible Automation Platform as an organization with surveyed job templates, see **[aap-playground-setup/](aap-playground-setup/README.md)**.

1. Follow **[aap-playground-setup/docs/CLICKOPS_GUIDE.md](aap-playground-setup/docs/CLICKOPS_GUIDE.md)** to create the seed org, inventory, AAP credential, project, and **Playground | Apply CaC** template.
2. Launch that template anytime to create or update the remaining objects and demo job templates from Config-as-Code under `aap-playground-setup/vars/`.

## Demos

| Demo | Topic |
|------|-------|
| [demo-strategy-free](demo-strategy-free/README.md) | [`strategy: free`](demo-strategy-free/README.md) — how the free execution strategy lets hosts run tasks independently instead of waiting at task barriers |
| [demo-ansible-forks-async](demo-ansible-forks-async/README.md) | [Forks and async jobs](demo-ansible-forks-async/README.md) — how `forks` limits parallel host work and how `async` + `poll: 0` frees controller forks while remote jobs run |
| [demo-hosts-advanced](demo-hosts-advanced/README.md) | [Normalizing messy host limit input](demo-hosts-advanced/README.md) — parsing AAP survey-style host lists into a clean dynamic `hosts:` target |
| [demo-when](demo-when/README.md) | [`when:` condition examples and pitfalls](demo-when/README.md) — version checks, boolean coercion, `default()` bugs, and AND/OR grouping |
| [demo-jinja2-filters](demo-jinja2-filters/README.md) | [Jinja2 built-in filters](demo-jinja2-filters/README.md) — runnable example of every stock Jinja2 filter (54 including aliases) |
| [demo-ansible-filters](demo-ansible-filters/README.md) | [ansible.builtin filters](demo-ansible-filters/README.md) — runnable example of every ansible-core filter plugin (70 filters) |
| [demo-lint-noqa](demo-lint-noqa/README.md) | [Suppressing `yaml[line-length]`](demo-lint-noqa/README.md) — `# noqa` vs yamllint for long lines |
| [demo-dynamic-inventory-csv](demo-dynamic-inventory-csv/README.md) | [CSV-driven dynamic inventory](demo-dynamic-inventory-csv/README.md) — one plugin, many inventory YAML filters from a single spreadsheet |
| [demo-dynamic-inventory-merge](demo-dynamic-inventory-merge/README.md) | [Merging flat inventories via plugin](demo-dynamic-inventory-merge/README.md) — layer INI/YAML/JSON sources with last-wins precedence |
| [demo-download-collection-tarball](demo-download-collection-tarball/README.md) | [Download a collection tarball from Automation Hub](demo-download-collection-tarball/README.md) — offline token → SSO → Hub API → S3 artifact; survey-friendly extra vars for AAP |
| [demo-satellite-sync-and-promote](demo-satellite-sync-and-promote/README.md) | [Satellite sync, wait, and lifecycle promote](demo-satellite-sync-and-promote/README.md) — sync/publish/DEV, then tag-driven promote to QA and PROD after validation |
| [demo-kerberos-winrm](demo-kerberos-winrm/README.md) | [Kerberos tickets for WinRM](demo-kerberos-winrm/README.md) — EE diagnostics before/after `win_ping`; run via **ansible-navigator** or AAP only |
| [demo-winrm-vs-psrp](demo-winrm-vs-psrp/README.md) | [WinRM vs PSRP timing (Kerberos)](demo-winrm-vs-psrp/README.md) — manual vs managed kinit, same Windows host, per-iteration comparison via Navigator/AAP EE |
| [demo-aap-connectivity](demo-aap-connectivity/README.md) | [AAP installer connectivity preflight](demo-aap-connectivity/README.md) — Redis cluster bus, Receptor mesh, PostgreSQL, and platform TCP checks against an installer inventory |
| [demo-aap-survey-pem-key](demo-aap-survey-pem-key/README.md) | [AAP Password survey PEM keys](demo-aap-survey-pem-key/README.md) — paste a masked multi-line private key into a Password survey; reconstruct PEM line breaks before downstream tasks |
| [demo-support-assist](demo-support-assist/README.md) | [infra.support_assist](demo-support-assist/README.md) — AAP API gather, OCP must-gather, sosreport, and RH case create/update with surveyed AAP job templates |
| [demo-aap-project-sync-collections](demo-aap-project-sync-collections/README.md) | [Project sync collection inventory](demo-aap-project-sync-collections/README.md) — parse galaxy install events from project updates (versions, download hosts, requirements/deps) across all or selected projects |


## Running a demo

```bash
cd demo-<name>
ansible-playbook playbook.yml
```

**Kerberos / Windows demos** ([demo-kerberos-winrm](demo-kerberos-winrm/README.md), [demo-winrm-vs-psrp](demo-winrm-vs-psrp/README.md)) must run via **ansible-navigator** or **AAP** inside an execution environment — not bare `ansible-playbook` on your workstation (they template `/etc/krb5.conf` and run `kinit` on the controller).

**PEM key survey demo** ([demo-aap-survey-pem-key](demo-aap-survey-pem-key/README.md)) requires `openssl` and `ssh-keygen` on the controller / execution environment.

Each demo README includes details on what to look for in the output, things to try, and — where relevant — how to adapt the pattern for use in Ansible Automation Platform (AAP).

## Pre-commit

This repo uses [pre-commit](https://pre-commit.com/) to scrub sensitive strings from staged files before each commit. Replacements live in a **local, gitignored config** — not in the script.

```bash
pip install pre-commit   # if needed
cp scripts/sanitize-strings.conf.example scripts/sanitize-strings.conf
# edit sanitize-strings.conf — one old:new pair per line
pre-commit install
```

Config format (`oldstring:newstring`, split on the first colon):

```text
your-hostname.example.com:lennysh-laptop
10.0.0.50:192.0.2.1
```

If the hook modifies files, re-stage and commit again:

```bash
git add -u
git commit
```

Run manually against all files:

```bash
pre-commit run sanitize-strings --all-files
```
