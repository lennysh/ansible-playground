# Ansible Demo Playground

Self-contained Ansible playbooks that demonstrate specific concepts, patterns, and pitfalls. Each demo lives in its own directory with a playbook and README explaining what it shows.

## Demos

| Demo | Topic |
|------|-------|
| [demo-free](demo-free/README.md) | [`strategy: free`](demo-free/README.md) — how the free execution strategy lets hosts run tasks independently instead of waiting at task barriers |
| [demo-hosts-advanced](demo-hosts-advanced/README.md) | [Normalizing messy host limit input](demo-hosts-advanced/README.md) — parsing AAP survey-style host lists into a clean dynamic `hosts:` target |
| [demo-when](demo-when/README.md) | [`when:` condition examples and pitfalls](demo-when/README.md) — version checks, boolean coercion, `default()` bugs, and AND/OR grouping |

## Running a demo

```bash
cd demo-<name>
ansible-playbook playbook.yml
```

Each demo README includes details on what to look for in the output, things to try, and — where relevant — how to adapt the pattern for use in Ansible Automation Platform (AAP).

## Pre-commit

This repo uses [pre-commit](https://pre-commit.com/) to scrub your real hostname from staged files before each commit. The real hostname lives in a **local, gitignored config** — not in the script.

```bash
pip install pre-commit   # if needed
cp scripts/sanitize-hostname.conf.example scripts/sanitize-hostname.conf
# edit sanitize-hostname.conf — set REAL_HOST to your FQDN
pre-commit install
```

If the hook modifies files, re-stage and commit again:

```bash
git add -u
git commit
```

Run manually against all files:

```bash
pre-commit run sanitize-hostname --all-files
```
