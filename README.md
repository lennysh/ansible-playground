# Ansible Demo Playground

Self-contained Ansible playbooks that demonstrate specific concepts, patterns, and pitfalls. Each demo lives in its own directory with a playbook and README explaining what it shows.

## Demos

| Demo | Topic |
|------|-------|
| [demo-strategy-free](demo-strategy-free/README.md) | [`strategy: free`](demo-strategy-free/README.md) — how the free execution strategy lets hosts run tasks independently instead of waiting at task barriers |
| [demo-hosts-advanced](demo-hosts-advanced/README.md) | [Normalizing messy host limit input](demo-hosts-advanced/README.md) — parsing AAP survey-style host lists into a clean dynamic `hosts:` target |
| [demo-when](demo-when/README.md) | [`when:` condition examples and pitfalls](demo-when/README.md) — version checks, boolean coercion, `default()` bugs, and AND/OR grouping |
| [demo-lint-noqa](demo-lint-noqa/README.md) | [Suppressing `yaml[line-length]`](demo-lint-noqa/README.md) — `# noqa` vs yamllint for long lines |
| [demo-dynamic-inventory-csv](demo-dynamic-inventory-csv/README.md) | [CSV-driven dynamic inventory](demo-dynamic-inventory-csv/README.md) — one plugin, many inventory YAML filters from a single spreadsheet |
| [demo-dynamic-inventory-merge](demo-dynamic-inventory-merge/README.md) | [Merging flat inventories via plugin](demo-dynamic-inventory-merge/README.md) — layer INI/YAML/JSON sources with last-wins precedence |


## Running a demo

```bash
cd demo-<name>
ansible-playbook playbook.yml
```

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
