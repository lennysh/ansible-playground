# random/run-commands — loop `command` over a list of params

Utility playbook: run an extra-var list through `ansible.builtin.command`, then
debug **stdout** and **stderr** when they are not empty.

This is not a teaching demo and is not loaded by **Playground | Apply CaC**.

## How to run

```bash
cd random/run-commands
ansible-playbook playbook.yml -i localhost, -c local -e @commands.example.yml
```

Against inventory hosts:

```bash
ansible-playbook playbook.yml -i inventories/hosts.yml -e @commands.yml
```

Optional extra var `target_hosts` overrides the play target (default `all`).

## `commands` list

Each item is either a **string** (`cmd`) or a **dict** of `ansible.builtin.command`
parameters plus task keywords. Unknown dict keys are ignored by the module.

| Key | Where it applies |
|-----|------------------|
| `cmd`, `argv`, `chdir`, `creates`, `removes`, `stdin`, `stdin_add_newline`, `strip_empty_ends`, `expand_argument_vars` | command module |
| `become`, `become_user`, `become_method`, `become_exe`, `become_flags` | task |
| `environment`, `no_log`, `timeout`, `changed_when`, `when` | task |
| `ignore_errors` | after debug — skip failing the play for that item |
| `name` | loop label only |

`become` is a **task** keyword, not a command module parameter. Put it on the
same list item; the playbook maps it onto the looped task.

Commands that fail still print stdout/stderr, then the play fails unless that
item sets `ignore_errors: true`.

### Example

```yaml
commands:
  - hostname
  - cmd: id
  - cmd: cat /etc/shadow
    become: true
  - argv: [ls, -la]
    chdir: /tmp
  - cmd: ls /no-such-path
    ignore_errors: true
```

AAP: set extra vars YAML (a survey textarea can be a YAML string; the playbook
runs it through `from_yaml`).
