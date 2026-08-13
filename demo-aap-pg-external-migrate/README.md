# demo-aap-pg-external-migrate — External → external PostgreSQL migration

Manual playbook that performs the same **`pg_dump -F custom | pg_restore --clean --if-exists`** stream the Automation Controller operator uses for **external DB → managed Postgres pod** migrations, but runs on any host/EE that already has PostgreSQL client tools so **both** endpoints can be external.

**CLI-only** (no AAP job template / CaC entry) — destructive ops tooling with DB passwords.

Provenance for the operator sources: **[EXTRACTION.md](EXTRACTION.md)**. Verbatim exports: **`_extracted/`**.

## Why the operator cannot do external → external

Operator `migrate_data.yml` always:

1. Finds the **managed** Postgres pod in the namespace  
2. `kubernetes.core.k8s_exec`s into it  
3. Runs `pg_dump` (to the *old* host from the old secret) piped into `pg_restore` (local to that pod)

The operator manager image itself has **no** `pg_dump`/`psql`. The managed pod also gets `PGPASSWORD_OLD` injected from the old configuration secret. Restore never passes `-h` because destination is localhost inside that pod.

If you only need the client tools + network reachability to two Postgres servers, the same pipe works external → external.

## Prerequisites

- Host or execution environment with `pg_dump`, `pg_restore`, and `psql` on `PATH` (versions compatible with both databases; prefer matching the server major)
- Network path from that host to **both** Postgres endpoints
- Destination user privileged enough for `pg_restore --clean --if-exists` (often superuser or owner of the target DB objects)
- Automation Controller (and other writers) **stopped** / scaled down before migrate — this playbook does not scale Deployments (operator does via `scale_down_deployment.yml`)

## Quick start

```bash
cd demo-aap-pg-external-migrate
cp vars/migrate.example.yml vars/migrate.yml   # edit secrets; gitignored pattern recommended

# Connectivity only
ansible-playbook playbook.yml -e @vars/migrate.yml -e migrate_check_only=true

# Real migrate
ansible-playbook playbook.yml -e @vars/migrate.yml -e migrate_confirm=true
```

## Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `source_pg_host/port/user/password/database` | (required) | Old / source DB |
| `dest_pg_host/port/user/password/database` | (required) | New / dest DB |
| `source_pg_sslmode` / `dest_pg_sslmode` | `prefer` | Passed as `PGSSLMODE` |
| `pg_dump_suffix` | `""` | Appended to `pg_dump` (same hook as operator) |
| `pg_restore_extra_args` | `--clean --if-exists` | Operator migrate_data flags |
| `grant_postgres_role` | `false` | If `true`, wraps restore with `GRANT/REVOKE postgres` like managed PG (needs `dest_pg_admin_*`) |
| `migrate_check_only` | `false` | Stop after `psql` connectivity checks |
| `migrate_confirm` | `false` | Must be `true` to run the stream when `require_confirm` is on |
| `keepalive_interval_seconds` | `60` | Same keepalive echo pattern as the operator |
| `hide_secrets` | `true` | Applied as task `no_log` (avoids reserved var name `no_log`) |

## Operator vs this playbook

| Step | Operator `migrate_data.yml` | This playbook |
|------|----------------------------|---------------|
| Where tools run | `k8s_exec` → managed PG pod | Localhost / EE shell |
| Source | `-h` from old secret | `source_pg_*` |
| Dest | localhost in pod + `POSTGRES_PASSWORD` | `dest_pg_*` with `-h/-p` |
| Scale down controllers | Yes | No (do it yourself) |
| `GRANT postgres TO …` | Always | Opt-in (`grant_postgres_role`) |
| Success check | (none on migrate_data; upgrade path checks `Successful`) | Requires `Successful` in stdout |

## Layout

```text
demo-aap-pg-external-migrate/
├── EXTRACTION.md          # when/how/version of the oc exec export
├── README.md
├── playbook.yml           # external → external migrate
├── vars/migrate.example.yml
└── _extracted/            # full /opt/ansible tree from the operator image + artifacts/
```

## Safety notes

- Always run `migrate_check_only=true` first.
- Do not point source and dest at the same host:port/database (playbook refuses).
- `--clean --if-exists` drops conflicting objects on the destination — treat dest as disposable or backed up.
- Keep secrets out of git; prefer `vars/migrate.yml` locally or Ansible Vault / AAP credentials if you later wrap this for AAP.
