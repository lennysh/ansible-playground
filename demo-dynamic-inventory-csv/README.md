# demo-dynamic-inventory-csv — One CSV, many inventories

Demonstrates building **multiple Ansible inventories from a single CSV file** using one custom inventory plugin. Each inventory source YAML file points at the same CSV but applies different filters and group rules — no duplicated Python per slice.

## What this shows

Many teams maintain host lists in spreadsheets or exports (Org, environment, cloud, team ownership, etc.). Instead of writing a separate inventory plugin for every combination of filters, this demo keeps **all rows in one CSV** and defines **views** as small YAML files:

| Concept | Where it lives |
|---------|----------------|
| Host data | `MSP_Managed.csv` (demo/fictional hostnames only) |
| Plugin logic | `plugins/inventory/csv_inventory.py` (single plugin) |
| Per-inventory filters & groups | `inventories/*.yaml` |

Each YAML file is a standalone inventory source you can pass to `ansible-inventory`, `ansible-playbook`, or an AAP inventory source.

## CSV columns

| Column | Example values | Purpose |
|--------|----------------|---------|
| `Org` | `Customer A`, `Customer B` | Customer / tenant |
| `Host` | `demo-ca-aws-pri-dev-app01` | Hostname (uppercased by the plugin) |
| `Cloud` | `AWS`, `Azure`, `VMWare` | Cloud provider |
| `Region` | `Primary`, `DR` | Region (DR used for AWS in this demo) |
| `Env` | `DEV`, `QA`, `PROD` | Environment |
| `LinuxTeam` | `TRUE` / `FALSE` | Linux team ownership flag |
| `WindowsTeam` | `TRUE` / `FALSE` | Windows team ownership flag |
| `WebServer` | `TRUE` / `FALSE` | Web tier flag |
| `DatabaseServer` | `TRUE` / `FALSE` | Database tier flag |

All columns become **host variables**, so standard Constructable options (`keyed_groups`, `groups`, `compose`) work on them.

## Sample inventory sources

| File | Filters (summary) | Typical use |
|------|-------------------|-------------|
| `MSP_Managed_CustomerA_AWS_All.yaml` | Customer A · AWS · all envs | Full AWS footprint |
| `MSP_Managed_CustomerA_AWS_DEV_QA.yaml` | Customer A · AWS · DEV/QA | Non-prod AWS changes |
| `MSP_Managed_CustomerA_AWS_Primary_All.yaml` | Customer A · AWS · Primary · all envs | Primary region only |
| `MSP_Managed_CustomerA_AWS_DR_All.yaml` | Customer A · AWS · DR · all envs | DR region only |
| `MSP_Managed_CustomerA_Azure_All.yaml` | Customer A · Azure · all envs | Azure workloads |
| `MSP_Managed_CustomerA_VMWare_All.yaml` | Customer A · VMWare · all envs | On-prem VMWare |
| `MSP_Managed_CustomerB_Azure_All.yaml` | Customer B · Azure · all envs | Second tenant |

See `inventories/` for the full set (including DEV/QA-only variants).

### Example inventory YAML

```yaml
plugin: csv_inventory
csv_file: ../MSP_Managed.csv
filters:
  Org:
    - Customer A
  Cloud:
    - AWS
  Env:
    - DEV
    - QA
always_groups:
  - msp_managed
keyed_groups:
  - prefix: region
    key: Region | lower
flag_groups:
  linux_team: LinuxTeam
  windows_team: WindowsTeam
  database_servers: DatabaseServer
  web_servers: WebServer
```

- **`filters`** — row must match every column (AND logic).
- **`always_groups`** — every matching host joins these groups (optional).
- **`flag_groups`** — host joins the group when the CSV column is `TRUE`.
- **`keyed_groups`** — dynamic groups from column values (`region_primary`, `region_dr`, …). Use Jinja filters on `key` for casing (`Region | lower`).

## How to run

Run commands from this directory so `ansible.cfg` picks up the custom plugin path.

```bash
cd demo-dynamic-inventory-csv

# Tree view of groups and hosts
ansible-inventory -i inventories/MSP_Managed_CustomerA_AWS_All.yaml --graph

# JSON inventory with host vars
ansible-inventory -i inventories/MSP_Managed_CustomerA_AWS_DEV_QA.yaml --list

# Hosts in a keyed group
ansible-inventory -i inventories/MSP_Managed_CustomerA_AWS_All.yaml --list | jq '.region_primary.hosts'
```

### Try these during a customer demo

1. **Same CSV, different slice** — compare `--graph` output for `_AWS_All` vs `_AWS_DEV_QA` vs `_AWS_DR_All`.
2. **Keyed groups** — show `region_primary` and `region_dr` appear automatically from the `Region` column.
3. **Flag groups** — show `linux_team` vs `windows_team` membership from boolean columns.
4. **Add a row** — edit `MSP_Managed.csv`, re-run `--graph`, and show the new host appears in the right inventories only.

## Plugin options

| Option | Description |
|--------|-------------|
| `csv_file` | Path to CSV (relative to the inventory YAML file) |
| `filters` | Column → list of allowed values |
| `always_groups` | Optional groups for all matching hosts (no plugin default) |
| `flag_groups` | Group name → CSV boolean column |
| `keyed_groups` | Standard Constructable keyed groups (see `ansible-doc -t inventory constructed`) |
| `groups` | Jinja2 conditional groups |
| `compose` | Jinja2 derived host variables |

## Demo data note

`MSP_Managed.csv` contains **fictional hostnames** (`demo-ca-*`, `demo-cb-*`) sized for presentations (~30 rows). It is not production data. Replace with your own export keeping the same column headers.

## AAP / production considerations

- Place the plugin in a **custom execution environment** or mount `plugins/inventory/` via `ansible.cfg` / `ANSIBLE_INVENTORY_PLUGINS`.
- Point each AAP inventory source at one YAML file under `inventories/`, or use an inventory plugin source synced from this repo.
- Sync the CSV from Git, S3, or a CMDB export; filters in YAML stay stable as the row count grows.
