# demo-dynamic-inventory-merge — Merging flat inventories via plugin

Demonstrates **inventory variable precedence** by combining multiple flat inventory files (INI, YAML, JSON) through a custom **inventory plugin**. Later sources override conflicting variables from earlier sources — the same rule Ansible applies when you pass multiple `-i` arguments.

## What this shows

| Concept | Where it lives |
|---------|----------------|
| Merge logic | `plugins/inventory/merge_inventory.py` |
| Source order & file list | `inventories/merged.yaml` |
| Sample INI / YAML / JSON inputs | `inventories/sources/` |

Ansible accepts several inventory formats (INI, YAML, JSON, and directory trees). When more than one source defines the same variable, **the last source wins**. This demo wraps that merge in one inventory source YAML so you can point a job template or playbook at a single `-i` entry while still layering sources in a controlled order.

Sample merge order in `inventories/merged.yaml`:

| Order | File | Format | Sets |
|-------|------|--------|------|
| 1 | `sources/01-base.ini` | INI | `app_port=8080`, `deployment_env=dev`, `shared_var=from_file_one`, `global_var=from_file_one`, `demo_label=base-ini` |
| 2 | `sources/02-overrides.yaml` | YAML | `deployment_env=staging`, `shared_var=from_file_two`, `global_var=from_file_two`, `only_in_two=true`, `host-a.app_port=9090` |
| 3 | `sources/03-final.json` | JSON | `shared_var=from_file_three`, `global_var=from_file_three`, `demo_label=final-json` |

Paths in `sources` are relative to `inventories/merged.yaml`, so `sources/01-base.ini` resolves to `inventories/sources/01-base.ini`.

Expected effective values on `host-a` after merge:

| Variable | Final value | Why |
|----------|-------------|-----|
| `app_port` | `9090` | Host var from YAML (file 2); not overridden by file 3 |
| `deployment_env` | `staging` | Group var from YAML overrides INI |
| `shared_var` | `from_file_three` | Overridden by each later file |
| `global_var` | `from_file_three` | Overridden by each later file |
| `demo_label` | `final-json` | JSON overrides INI |
| `only_in_two` | `true` | Only defined in file 2; nothing later replaces it |

On `host-b`, `app_port` stays `8080` because only `host-a` gets a host-level override in file 2.

## How it works

`merge_inventory` is a custom inventory plugin registered via `ansible.cfg`. Each inventory source YAML lists `sources` in merge order. The plugin:

1. Resolves each path relative to the inventory YAML file.
2. Runs `ansible-inventory --list` with one `-i` per source, in that order.
3. Imports the merged JSON into the active inventory.

Using `ansible-inventory` internally means **any format Ansible can parse** works as an input source — you do not need separate parsers in the plugin.

### Example inventory YAML

```yaml
plugin: merge_inventory
sources:
  - sources/01-base.ini
  - sources/02-overrides.yaml
  - sources/03-final.json
```

Paths are relative to the inventory YAML file unless absolute.

## How to run

Run commands from this directory so `ansible.cfg` picks up the custom plugin path.

```bash
cd demo-dynamic-inventory-merge

ansible-inventory -i inventories/merged.yaml --list
ansible-inventory -i inventories/merged.yaml --host host-a

ansible-playbook -i inventories/merged.yaml playbook.yml
```

Compare precedence by reordering `sources` in `inventories/merged.yaml`, then re-run `--list` or the playbook.

## Sample output

### Merged inventory (`ansible-inventory --list`)

<!-- Paste raw `ansible-inventory -i inventories/merged.yaml --list` output below -->

```json
{
    "_meta": {
        "hostvars": {
            "host-a": {
                "app_port": 9090,
                "demo_label": "final-json",
                "deployment_env": "staging",
                "global_var": "from_file_three",
                "only_in_two": true,
                "shared_var": "from_file_three"
            },
            "host-b": {
                "app_port": 8080,
                "demo_label": "final-json",
                "deployment_env": "staging",
                "global_var": "from_file_three",
                "only_in_two": true,
                "shared_var": "from_file_three"
            }
        }
    },
    "all": {
        "children": [
            "ungrouped",
            "webservers"
        ]
    },
    "webservers": {
        "hosts": [
            "host-a",
            "host-b"
        ]
    }
}
```

The `_meta.hostvars` block is the merged result — compare `host-a` vs `host-b` for host-level overrides, and shared keys like `shared_var` for last-wins group/all vars.

### Playbook run

<!-- Paste raw `ansible-playbook -i inventories/merged.yaml playbook.yml` output below -->

```text
PLAY [Demonstrate merged inventory variable precedence] ************************

TASK [Show effective variables after merge (later sources win)] ****************
ok: [host-a] => {
    "msg": {
        "app_port": "9090",
        "demo_label": "final-json",
        "deployment_env": "staging",
        "global_var": "from_file_three",
        "inventory_hostname": "host-a",
        "only_in_two": true,
        "shared_var": "from_file_three"
    }
}
ok: [host-b] => {
    "msg": {
        "app_port": "8080",
        "demo_label": "final-json",
        "deployment_env": "staging",
        "global_var": "from_file_three",
        "inventory_hostname": "host-b",
        "only_in_two": true,
        "shared_var": "from_file_three"
    }
}

PLAY RECAP *********************************************************************
host-a                     : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
host-b                     : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Note the precedence in the output:

- **`host-a.app_port`** is `9090` (YAML host override) while **`host-b.app_port`** stays `8080` (INI group default).
- **`shared_var`**, **`global_var`**, and **`demo_label`** all reflect file 3 — the last source in the merge list.
- **`deployment_env`** is `staging` from file 2; file 3 does not redefine it.
- **`only_in_two`** survives from file 2 because nothing later replaces it.

## Things to try

1. Move `sources/03-final.json` above `sources/02-overrides.yaml` in `merged.yaml` and note which variables change.
2. Remove a source and confirm values fall back to the next earliest definition.
3. Add a fourth file under `inventories/sources/` in another format (for example a one-host INI snippet) and observe overrides.
4. Copy `merged.yaml` to a new file with a different `sources` list to define another merged view (same pattern as the CSV demo's many YAML files).

## Plugin options

| Option | Description |
|--------|-------------|
| `sources` | Ordered list of inventory paths to merge; later entries win on conflicts |

## AAP note

Place the plugin in a **custom execution environment** or mount `plugins/inventory/` via `ansible.cfg` / `ANSIBLE_INVENTORY_PLUGINS`. Point the inventory source at `inventories/merged.yaml` (or a copy with your own `sources` list). Merge order is controlled entirely by that YAML file.
