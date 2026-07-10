# AAP installer connectivity preflight

TCP connectivity checks derived from the **containerized AAP installer** inventory groups and default ports. Run this against a customer's installer `inventory` file **before** `ansible.containerized_installer.install` to catch firewall and routing gaps (Redis cluster bus, Receptor mesh, external PostgreSQL, etc.).

Useful for multi-region topologies where `curl telnet://host:6379` passes but **16379** (Redis cluster bus) or **27199** (Receptor) does not.

## Quick start

```bash
cd demo-aap-connectivity
cp vars/connectivity.example.yml vars/connectivity.yml

# Example inventory from aap-notes (adjust path to your copy)
ansible-playbook \
  -i ../github.com_lennysh/aap-notes/config-examples/AAP25/containerized/inventory-example \
  playbook.yml \
  -e @vars/connectivity.yml \
  --limit 'gateway1.example.org,controller1.example.org'   # dry-run against examples (will fail — expected)
```

Against a real customer inventory:

```bash
ansible-playbook \
  -i /path/to/customer/inventory \
  playbook.yml \
  -e @vars/connectivity.yml
```

Redis checks only:

```bash
ansible-playbook -i /path/to/inventory playbook.yml --tags redis
```

## Suites

| Suite | Tag | Source hosts | Targets | Ports (defaults) |
| :--- | :--- | :--- | :--- | :--- |
| `redis` | `redis` | `[redis]` | all other `[redis]` | `6379`, `16379` (cluster bus when `redis_mode=cluster`) |
| `receptor` | `receptor` | `[automationcontroller]` + `[execution_nodes]` | same mesh | `27199` |
| `postgresql` | `postgresql` | each service group | `*_pg_host` from inventory | `5432` (or `*_pg_port`) |
| `platform` | `platform` | `[automationgateway]` | each component host | nginx HTTPS ports (8443, 8444, …) |
| `pcp` | `pcp` | control-plane hosts | peer control-plane hosts | `44321`, `44322` |

Port defaults match `ansible.containerized_installer` role defaults and can be overridden in the installer inventory (`redis_port`, `receptor_port`, `gateway_nginx_https_port`, etc.).

## Output

- Markdown report: `aap-connectivity-report.md` (path set via `aap_connectivity_report_path`)
- Playbook **fails** when any probe fails (`aap_connectivity_fail_on_error: true`, default)
- Matrix shows **source → target:port** for every probe (same shape GSS asks for on Redis cases)

## Variables

See `vars/connectivity.example.yml` and `roles/aap_connectivity/defaults/main.yml`.

| Variable | Purpose |
| :--- | :--- |
| `aap_connectivity_suites` | List of suites to run |
| `aap_connectivity_timeout` | Per-probe wait timeout (seconds) |
| `aap_connectivity_redis_mode` | `cluster` or `standalone` (reads `redis_mode` from inventory by default) |
| `aap_connectivity_fail_on_error` | Fail playbook on any failed probe |

## Inventory expectations

Designed for **containerized** installer inventories (`[automationgateway]`, `[redis]`, …). Reference examples:

- [aap-notes/config-examples](https://github.com/lennysh/aap-notes/tree/main/config-examples) — `AAP25/containerized/inventory-example`, `AAP26/containerized/inventory-example`, etc.
- Installer dumps under `config-examples/.installer-dumps/` document authoritative port defaults.

RPM-based installs share Receptor mesh concepts; Redis topology differs (often standalone on gateway). Extend `aap_connectivity_suites` or add an `rpm` deployment profile if needed.

## AAP job template

Use `playbook-aap.yml`. Attach the customer installer inventory to the job template and pass `aap_connectivity_suites` via survey.

## What this does *not* check

- PostgreSQL authentication (TCP only — use installer preflight for `postgresql_ping`)
- TLS handshakes / certificate validation
- Redis cluster *formation* (only network reachability)
- Ansible SSH connectivity (run `ansible ping` separately)

## Related installer error

Containerized Redis cluster init failure:

```text
Please check the network and firewall configuration (6379/16379)
```

That message comes from `ansible.containerized_installer` `roles/redis/tasks/cluster.yml` when `CLUSTER MEET` cannot complete — exactly what the `redis` suite exercises.
