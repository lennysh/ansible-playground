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

Each demo README includes details on what to look for in the output and things to try.
