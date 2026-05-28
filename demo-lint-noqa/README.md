# demo-lint-noqa — Suppressing `yaml[line-length]`

Demonstrates how ansible-lint enforces **maximum line length** (160 characters by default via `yaml[line-length]`) and how to suppress violations correctly with `# noqa` or yamllint directives.

Each task name includes the expected lint outcome (`FAIL` or `PASS`) so you can compare against `ansible-lint` output.

## What this shows

ansible-lint delegates YAML line-length checks to **yamllint**. When a line exceeds 160 characters, you get:

```text
yaml[line-length]: Line too long (213 > 160 characters)
playbook.yml:10
```

Suppressing that violation depends on **where** the long line lives in the file — not all `# noqa` placements work.

| Task | Approach | Lint result |
|------|----------|-------------|
| 1 | Long line inside `msg: \|` block scalar | **FAIL** — no noqa on the violating line |
| 2 | Long single-line `msg` with `# noqa: yaml[line-length]` at end of that line | **PASS** |
| 3 | Block scalar with `# yamllint disable rule:line-length` before `msg:` | **PASS** |

## How it works

The playbook has three tasks on `localhost`:

1. **Task 1** — Uses a literal block scalar (`msg: \|`) with one intentionally long content line. This is the common case when pasting ansible output or prose into a README. ansible-lint reports the violation on the **content line** inside the block (line 10 in `playbook.yml`).

2. **Task 2** — Same long string, but as a **single quoted line** with `# noqa: yaml[line-length]` at the end of that physical line. This is the correct way to suppress a line-based rule for inline YAML values.

3. **Task 3** — Same block scalar as task 1, but wrapped with **yamllint** disable/enable comments before and after `msg:`. This is the reliable approach when you need multiline `|` or folded `>-` blocks and cannot put noqa on the long line itself.

## `# noqa` vs task-based rules

ansible-lint supports two kinds of suppressions:

- **Task-based rules** — `# noqa` on the task `name:` line (or module parameters) can skip rules for the whole task.
- **Line-based rules** — `# noqa` must appear at the **end of the exact line** that triggers the violation.

`yaml[line-length]` is **line-based**. Placing `# noqa: yaml[line-length]` on the task name does **not** suppress a long line inside `msg:`.

### Correct: noqa on the long line

```yaml
- name: Demo yaml[line-length] with noqa on the long line (expect PASS)
  ansible.builtin.debug:
    msg: "This debug message is intentionally written as one long line..."  # noqa: yaml[line-length]
```

### Incorrect placements (do not work for block content)

```yaml
# On task name — only covers the name line, not line 10 inside msg:
- name: Long msg demo  # noqa: yaml[line-length]

# After the block — not on the violating line:
    msg: |
      very long line...
    # noqa: yaml[line-length]

# Inside a | block — becomes part of the string (or is ignored):
    msg: |
      very long line...  # noqa: yaml[line-length]
```

See [ansible-lint#2271](https://github.com/ansible/ansible-lint/issues/2271) for why block scalars need yamllint instead of noqa.

## Block scalars: use yamllint directives

When the long line must stay inside `msg: |` or `>-`, wrap the key with yamllint control comments:

```yaml
- name: Demo yaml[line-length] with yamllint disable for block scalar (expect PASS)
  ansible.builtin.debug:
    # yamllint disable rule:line-length
    msg: |
      This debug message is intentionally written as one long line...
    # yamllint enable rule:line-length
```

Re-enable the rule after the block so later tasks are still checked.

## Things to try

- Move `# noqa: yaml[line-length]` from task 2 onto the task `name:` line — task 2 should start failing.
- Remove the yamllint disable/enable comments from task 3 — task 3 should fail on the long line inside the block.
- Shorten the string in task 1 below 160 characters — the playbook should pass lint entirely.
- Run with verbose output: `ansible-lint -v playbook.yml`

## How to run

Requires [ansible-lint](https://ansible.readthedocs.io/projects/lint/) and ansible-core installed.

```bash
cd demo-lint-noqa
ansible-lint playbook.yml
```

Expected: **1 failure** on line 10 (task 1 only).

The playbook itself is valid and can be executed:

```bash
ansible-playbook playbook.yml
```

## Sample output

```shell
WARNING  Listing 1 violation(s) that are fatal
yaml[line-length]: Line too long (213 > 160 characters)
playbook.yml:10

Read documentation for instructions on how to ignore specific rule violations.

# Rule Violation Summary

  1 yaml profile:basic tags:formatting,yaml

Failed: 1 failure(s), 0 warning(s) on 2 files. Last profile that met the validation criteria was 'min'.
```
