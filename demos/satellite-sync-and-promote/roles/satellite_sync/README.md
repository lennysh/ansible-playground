# satellite_sync role

Kicks off **repository or product synchronization** on Red Hat Satellite and blocks until each sync **Foreman task** completes.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `satellite_sync_targets` | `[]` (required) | List of dicts with `product` (required) and optional `repository` |
| `satellite_sync_wait_timeout` | `7200` | Seconds passed to `redhat.satellite.wait_for_task` per sync |

Inherited from the play (see `group_vars/all/satellite.example.yml`): `satellite_organization`, and Satellite API credentials via `module_defaults`.

## Behavior

1. `redhat.satellite.repository_sync` — one API call per target. Omit `repository` to sync every repository in the product.
2. `redhat.satellite.wait_for_task` — polls the task UUID returned in `sync_result.task.id` until success or timeout.

## Tags

`sync`
