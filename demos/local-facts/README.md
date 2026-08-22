# demos/local-facts — Persist custom facts with `facts.d`

Demonstrates **local facts** in two ways: the **default** host directory
(`/etc/ansible/facts.d`) and a **custom** `fact_path`. Each part writes a `*.fact` file,
`cat`s it before and after, re-gathers with `setup`, and cleans up in an `always` block.

## CLI demo vs. AAP usage

| CLI demo scaffolding | In AAP (`playbook-aap.yml`) |
|----------------------|-----------------------------|
| `hosts: localhost` + `connection: local` | `hosts: all` — target your inventory |
| Part 1 `become: true` on the play | Job template has **Privilege Escalation** enabled (`become_enabled: true`) |
| Part 2 no become | Part 2 play sets `become: false` explicitly |
| Same shared task file | `tasks/demo_local_facts_flow.yml` |

Ready-to-use job template: **Demo \| Local Facts** (created by **Playground \| Apply CaC** when
**Local Facts** is selected in the setup survey). Attach a machine credential with become access
for Part 1 (`/etc/ansible/facts.d`). Part 2 only needs write access to `/tmp` on each host.

```bash
# Custom path only (no /etc/ansible/facts.d / become needed):
ansible-playbook playbook-aap.yml --tags custom-facts
```

## Two methods

| | Part 1 — default path | Part 2 — custom `fact_path` |
|---|---|---|
| Directory | `/etc/ansible/facts.d` | `/tmp/ansible-playground-local-facts-demo` |
| How Ansible finds it | Omit `fact_path` on `setup` / `gather_facts` | Pass `fact_path:` on `setup` (or as a play keyword) |
| Privileges | `become: true` (system path) | None (demo-owned `/tmp` tree) |
| Fact file created | `playground-default.fact` | `playground-custom.fact` |
| `ansible_local` key | `ansible_local.playground-default` | `ansible_local.playground-custom` |
| Cleanup | **Only** `playground-default.fact` — other files in `facts.d` are left alone | Whole demo directory (nothing else should be there) |

Part 1 is the production pattern. Part 2 is useful for labs, CI, or when you cannot write
under `/etc`.

## What each part shows

| Step | What happens |
|------|----------------|
| Clean slate | Remove only our demo artifact(s) — a single file (Part 1) or directory (Part 2) |
| Initial `setup` | Our fact key is **undefined** — nothing on disk yet |
| `cat` before | File does not exist |
| Write `*.fact` | JSON local fact file created |
| `cat` after | File contents visible on disk |
| Without re-gather | Fact key is **still undefined** in the same play |
| `setup` again | `ansible_local.<key>` now has values |
| `always` cleanup | Same scope as clean slate — file only vs whole demo dir |

## Key concepts

- Local facts live in `facts.d` as files ending in `.fact` (JSON, INI, or executable scripts).
- Ansible exposes them under **`ansible_local.<filename_without_extension>`**.
- **Default `fact_path`** is `/etc/ansible/facts.d` when you omit the parameter on `setup` or
  use `gather_facts: true` without a play-level `fact_path`.
- `gather_facts` runs once at play start. After you create or change a `.fact` file, run
  **`ansible.builtin.setup`** with `filter: ansible_local` to reload them in the same play.
- `set_fact` is in-memory for the play (or controller cache with `cacheable: true`) — it does
  **not** write host-local facts the way `facts.d` does.

## How to run

```bash
cd demos/local-facts
ansible-playbook playbook.yml

# Custom path only (no sudo):
ansible-playbook playbook.yml --tags custom-facts
```

Part 1 requires passwordless `become` (or `--ask-become-pass`) to write under
`/etc/ansible/facts.d`. If `become` is unavailable, Part 1 is skipped with a message and Part 2
still runs.

Look for:

1. Part 1 note mentioning cleanup of **only** `playground-default.fact`
2. `undefined` → write → `cat` → still `undefined` → re-gather → populated fact
3. Part 2 repeating the same flow with `fact_path` set explicitly

## Things to try

- List `/etc/ansible/facts.d` before and after Part 1 — only `playground-default.fact` appears
  and disappears; any pre-existing `*.fact` files remain.
- Set `fact_path: /tmp/ansible-playground-local-facts-demo` as a **play keyword** on Part 2 and
  remove `fact_path` from the `setup` tasks in the included file — same behavior.
- Add a follow-on play with `gather_facts: true` and no `fact_path` to see facts picked up
  automatically on the next play (after removing cleanup temporarily).

## Sample output

<!-- Paste raw `ansible-playbook playbook.yml` output below -->

```text
PLAY [Part 1 — default facts.d (/etc/ansible/facts.d)] *************************

TASK [Note — setup and gather_facts use /etc/ansible/facts.d when fact_path is omitted] ***
ok: [localhost] => {
    "msg": "Default fact_path is /etc/ansible/facts.d. setup is called without fact_path so Ansible reads that directory. Cleanup removes only playground-default.fact, not other files in facts.d."
}

# When become works, Part 1 continues through the shared flow (same steps as Part 2
# below) using ansible_local.playground-default. If become fails, you see:

TASK [Part 1 skipped — /etc/ansible/facts.d requires working become/root] ******
ok: [localhost] => {
    "msg": "Could not write to /etc/ansible/facts.d (become failed). Part 2 still runs below. Re-run Part 1 on a host with sudo access."
}

PLAY [Part 2 — custom fact_path (/tmp/...)] ************************************

TASK [[custom fact_path] Show ansible_local.playground-custom is absent before write] ***
ok: [localhost] => {
    "msg": "ansible_local.playground-custom is undefined (expected: undefined)"
}

TASK [[custom fact_path] Display on-disk fact file before write] ***************
ok: [localhost] => {
    "msg": "(file does not exist yet)"
}

TASK [[custom fact_path] Display on-disk fact file after write] ****************
ok: [localhost] => {
    "demo_cat_after.stdout": {
        "demo": true,
        "message": "Hello from facts.d",
        "method": "custom fact_path",
        "source": "ansible-playground local-facts demo"
    }
}

TASK [[custom fact_path] Show ansible_local.playground-custom still absent without re-gather] ***
ok: [localhost] => {
    "msg": "ansible_local.playground-custom is still undefined in this play until setup runs again (expected: undefined)"
}

TASK [[custom fact_path] Show ansible_local.playground-custom now returns values] ***
ok: [localhost] => {
    "msg": {
        "demo": true,
        "message": "Hello from facts.d",
        "method": "custom fact_path",
        "source": "ansible-playground local-facts demo"
    }
}

PLAY RECAP *********************************************************************
localhost : ok=19   changed=3    unreachable=0    failed=0    skipped=0    rescued=1
```
