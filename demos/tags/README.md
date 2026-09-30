# demos/tags — Ansible tags (`always`, `never`, and selective runs)

A runnable walkthrough of [Ansible tags](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_tags.html), with emphasis on the special tags **`always`** and **`never`**.

Task names include the expected outcome for a **default** run (no `--tags` / `--skip-tags`). Compare against the matrices below when you filter.

Tag selection happens during playbook pre-processing: tasks that do not match are **omitted from the play** (they do not print as `skipping:` and do not bump `skipped=` in the RECAP). That is different from a `when:` skip.

## How tags work (two steps)

1. **Define** tags on tasks (or blocks / plays / roles / imports) with the `tags:` keyword.
2. **Select or skip** those tags when you run the playbook (`--tags` / `--skip-tags`, or AAP Job Tags / Skip Tags).

`tags:` never selects work by itself — it only labels tasks. Selection happens at run time.

## Special tags: `always` and `never`

| Tag | Default behavior | How to change it |
|-----|------------------|------------------|
| `always` | Runs with the default (`all`) **and** with any `--tags` selection | Omit with `--skip-tags always`, or `--skip-tags <other>` if the task also has that other tag |
| `never` | Omitted with the default (`all`) | Request with `--tags never`, `--tags <other>` if the task also has that other tag, or `--tags all,never` |

Related selection keywords (CLI / Job Tags field):

- `all` — default; tagged + untagged, but still excludes `never`
- `tagged` — only tasks that have at least one tag (`never` still overrides)
- `untagged` — only tasks with no tags (`always` still overrides)

Skipping wins over including: `--tags config --skip-tags config` runs nothing tagged only `config`.

## Playbook tasks at a glance

| # | Tags | Default run |
|---|------|-------------|
| 1 | `always` | RUN |
| 2 | *(none)* | RUN |
| 3 | `packages` | RUN |
| 4 | `config` | RUN |
| 5 | `always`, `config` | RUN |
| 6 | `never`, `debug` | OMITTED |
| 7 | `never` | OMITTED |
| 8a / 8b | `deploy` (on block) | RUN |

Default PLAY RECAP: `ok=7`, `skipped=0` (tasks 6 and 7 never enter the play).

## Scenario matrices

Use these as a checklist while reading the output. `R` = runs, `—` = omitted (not in the play).

### Default vs selective `--tags`

| Task | default | `--tags config` | `--tags packages` | `--tags debug` | `--tags never` | `--tags all,never` |
|------|---------|-----------------|-------------------|----------------|----------------|--------------------|
| 1 `always` | R | R | R | R | R | R |
| 2 untagged | R | — | — | — | — | R |
| 3 `packages` | R | — | R | — | — | R |
| 4 `config` | R | R | — | — | — | R |
| 5 `always,config` | R | R | R | R | R | R |
| 6 `never,debug` | — | — | — | R | R | R |
| 7 `never` | — | — | — | — | R | R |
| 8 deploy block | R | — | — | — | — | R |

### `--skip-tags` (including the `always` + other-tag pitfall)

| Task | `--skip-tags always` | `--skip-tags config` | `--skip-tags packages` |
|------|----------------------|----------------------|------------------------|
| 1 `always` | — | R | R |
| 2 untagged | R | R | R |
| 3 `packages` | R | R | — |
| 4 `config` | R | — | R |
| 5 `always,config` | — | — | R |
| 6 / 7 `never…` | — | — | — |
| 8 deploy | R | R | R |

Task **5** is the important teaching point: combining `always` with another tag means `--skip-tags config` omits it even though it is also `always`.

## CLI vs AAP

| CLI | AAP |
|-----|-----|
| `ansible-playbook playbook.yml` | Launch **Demo \| Tags** (localhost inventory) |
| `--tags config` | Job Tags prompt: `config` |
| `--skip-tags always` | Skip Tags prompt: `always` |
| `--tags all,never` | Job Tags: `all,never` |
| `--list-tags` / `--list-tasks` | Use CLI against the project checkout (Controller does not surface `--list-tags`) |

CaC sets `ask_tags_on_launch` and `ask_skip_tags_on_launch` so each launch can try a different scenario.

## How to run

```bash
cd demos/tags

# Default — always/never behavior
ansible-playbook playbook.yml

# Discover tags without running
ansible-playbook playbook.yml --list-tags

# Selective runs
ansible-playbook playbook.yml --tags config
ansible-playbook playbook.yml --tags debug
ansible-playbook playbook.yml --tags never
ansible-playbook playbook.yml --tags all,never

# Skip paths (watch task 5 with --skip-tags config)
ansible-playbook playbook.yml --skip-tags always
ansible-playbook playbook.yml --skip-tags config

# Preview which tasks would run
ansible-playbook playbook.yml --tags config --list-tasks
```

## Things to try

- `--tags tagged` — omits untagged task 2; `always` still runs; `never` tasks stay omitted.
- `--tags untagged` — task 2 plus every `always` task (1 and 5).
- `--tags config --skip-tags config` — only task 1 (`always` alone); task 5 is omitted because skip wins on its `config` tag.
- Add another normal tag on task 6 (for example `verbose`) and confirm `--tags verbose` also unlocks the `never` task.

## Sample output (default run)

```text
PLAY [Tags — always, never, and selective execution] ***************************

TASK [1. always — safety / preflight (expect: RUN unless skipped)] *************
ok: [localhost] => {
    "msg": "Tagged always — Ansible runs this with the default (all) and with any --tags selection, unless you --skip-tags always (or skip another tag also on this task)."
}

TASK [2. untagged — no tags keyword (expect: RUN with default; OMITTED with --tags X)] ***
ok: [localhost] => {
    "msg": "No tags — runs when you use the default (all) or --tags untagged; omitted when you pass specific tags such as --tags config."
}

TASK [3. packages — normal tag (expect: RUN with default)] *********************
ok: [localhost] => {
    "msg": "Tagged packages — select with --tags packages"
}

TASK [4. config — normal tag (expect: RUN with default)] ***********************
ok: [localhost] => {
    "msg": "Tagged config — select with --tags config"
}

TASK [5. always + config — always, unless you skip always or config] ***********
ok: [localhost] => {
    "msg": "Tagged always,config — runs by default and with --tags config; omitted by --skip-tags always OR --skip-tags config."
}

TASK [8a. deploy — first block task (expect: RUN with default)] ****************
ok: [localhost] => {
    "msg": "Block-level deploy tag is inherited by this task"
}

TASK [8b. deploy — second block task (expect: RUN with default)] ***************
ok: [localhost] => {
    "msg": "Both block tasks run together when deploy is selected (or with all)"
}

PLAY RECAP *********************************************************************
localhost                  : ok=7    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Tasks 6 and 7 (`never`) do not appear at all on a default run — they are omitted during pre-processing, not skipped with a `when:`.
