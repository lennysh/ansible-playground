# Ansible Demo Playground

Self-contained Ansible playbooks that demonstrate specific concepts, patterns, and pitfalls. Demos live under **[demos/](demos/README.md)** — each directory has a playbook and README.

## AAP bootstrap

To load these demos into Ansible Automation Platform as an organization with surveyed job templates, see **[aap-playground-setup/](aap-playground-setup/README.md)**.

1. Follow **[aap-playground-setup/docs/CLICKOPS_GUIDE.md](aap-playground-setup/docs/CLICKOPS_GUIDE.md)** to create the seed org, inventory, AAP credential, project, and **Playground | Apply CaC** template.
2. Launch that template anytime to create or update the remaining objects and demo job templates from Config-as-Code under `aap-playground-setup/vars/`.

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

## Related repos

- [cheat-sheets](https://github.com/lennysh/cheat-sheets) — copy-paste notes (AAP, Automation Orchestrator, OpenShift, …)
- [eda-playground](https://github.com/lennysh/eda-playground) — Event-Driven Ansible
- [argocd-playground](https://github.com/lennysh/argocd-playground) — Argo CD GitOps for AAP, Automation Orchestrator, and related apps on OpenShift
