# Extraction provenance — Automation Controller operator migrate_data

Captured for reverse-engineering an external→external PostgreSQL migration
playbook that mirrors the operator's external→managed path.

## When / where

| Field | Value |
|-------|-------|
| Initial selective export (UTC) | 2026-07-30T16:12:01Z (`oc exec … cat` of migrate-related files) |
| Full `/opt/ansible` export (UTC) | 2026-07-30T16:49:14Z (see `artifacts/full-export-info.txt`) |
| Cluster API | `https://api.cluster.example.com:6443` |
| Namespace / project | `aap24-db-test` |
| Pod | `automation-controller-operator-controller-manager-7bcb69d987ccf` |
| Container | `automation-controller-manager` |
| How exported (full tree) | `oc exec … -- tar -C /opt/ansible -cf -` (excludes `.ansible/tmp`, `__pycache__`, `*.pyc`) → `_extracted/` |

`_extracted/` is a verbatim mirror of `/opt/ansible` from the operator image (~9 MiB): `roles/`, `playbooks/`, `watches.yaml`, and bundled collections under `.ansible/collections/`. Operator-owned roles only: **installer**, **backup**, **restore**, **common** (94 role files). Provenance extras live in `_extracted/artifacts/` (not from the image).

Inventory: `_extracted/artifacts/full-export-inventory.txt`  
Checksums (roles + playbooks): `_extracted/artifacts/sha256sums-roles-playbooks.txt`

## Operator / CSV version

| Field | Value |
|-------|-------|
| CSV | `aap-operator.v2.4.0-0.1784071413` |
| Spec version | `2.4.0+0.1784071413` |
| Subscription | `ansible-automation-platform-operator` |
| Channel | `stable-2.4` |
| Catalog source | `redhat-operators` |
| Display name | Ansible Automation Platform |

## Images

| Role | Image |
|------|-------|
| Operator manager container | `registry.redhat.io/ansible-automation-platform-24/controller-rhel8-operator@sha256:0661d2bd9013757c47d4eb5e14aef872522b5c1ba1d927156d74d1ea6d3e8ab4` |
| Related controller | `registry.redhat.io/ansible-automation-platform-24/controller-rhel8@sha256:538fa03eea43fa5734e8992e2f7d79c24b892cba0bed2eb7996c8df7192170ae` |
| Related managed postgres | `registry.redhat.io/rhel8/postgresql-15@sha256:867820c0cc6cdf67b4fc6525b53a567ab69f8e2742dafacc91ef0024ea6f3e12` |

Base OS inside operator container: RHEL 8.10.  
`pg_dump` / `psql` are **not** present on the operator manager image (`command -v` → missing; `postgresql` RPM not installed). Migration always runs via `kubernetes.core.k8s_exec` into the managed Postgres pod.

## Layout of `_extracted/` (full operator ansible tree)

```text
_extracted/
├── watches.yaml
├── playbooks/awx.yml
├── roles/
│   ├── installer/     # migrate_data, database_configuration, initialize_django, …
│   ├── backup/
│   ├── restore/
│   └── common/
├── .ansible/collections/ansible_collections/   # kubernetes, community.docker, operator_sdk, cloud.common
└── artifacts/         # our provenance notes (not from the image)
```

Migration-relevant entrypoints (still the ones that matter most):

| Image path | Notes |
|------------|-------|
| `roles/installer/tasks/migrate_data.yml` | external→managed `pg_dump \| pg_restore` via `k8s_exec` |
| `roles/installer/tasks/database_configuration.yml` | loads old/new secrets; imports `migrate_data.yml` |
| `roles/installer/tasks/initialize_django.yml` | post-deploy init; legacy `tower` queue unregister only |
| `roles/installer/tasks/cleanup.yml` | K8s secret ownerReferences — not DB UUID scrub |
| `roles/installer/tasks/upgrade_postgres.yml` | managed PG major-version dump\|restore sibling |
| `roles/installer/files/pre-stop/*` | `disable_instance` on pod termination |
| `playbooks/awx.yml` | reconcile entry playbook |

`migrate_data.yml` inside the image: mtime `2026-07-14 09:55:42 UTC`, size `3196` bytes.

Earlier selective SHA-256s (still valid after full re-export of the same image content):

```text
a71682b6e7784ba80c35283fc19769fcc39807d1114b18225bf14a66199de352  migrate_data.yml
00ccdf6d6d2c48af31c8ac0b64cad8523d0dcdf5a128102b2d9f94d31b62cd66  database_configuration.yml
61d024df08570367c8a45ed7c1f10d10e7a7944b19222e2e3fb0b63cb2569e9e  upgrade_postgres.yml
eac28bc637ae49bc99290c9759403b5c4aab4b29ba6d597bccbb17ce7c97dde3  scale_down_deployment.yml
8c57da78e77f72669d9a0743d789ca521cbce3417dc41c1d0b57bef3201e452d  postgres.yaml.j2
```

## How the operator triggers migration

1. Reconcile playbook (`/opt/ansible/playbooks/awx.yml` / runtime copy) runs the `installer` role.
2. `database_configuration.yml` loads:
   - current postgres secret (`postgres_configuration_secret` or `<name>-postgres-configuration`)
   - **old** postgres secret (`old_postgres_configuration_secret` or `<name>-old-postgres-configuration`)
3. When `old_pg_config` has resources **and** CR status `migratedFromSecret` is unset, it `import_tasks: migrate_data.yml`.
4. `migrate_data.yml`:
   - Decodes old secret → source host/user/pass/db/port
   - Finds the **managed** postgres pod (`app.kubernetes.io/instance=postgres-{{ supported_pg_version }}-{{ name }}`)
   - Scales controller Deployments to 0 (`scale_down_deployment.yml`)
   - Builds `pg_dump -h <old> … -F custom` and `pg_restore --clean --if-exists -U <dbuser> -d <dbname>` (**no** `-h` on restore — restore targets localhost inside the managed pod)
   - `k8s_exec` into the managed pod:
     - keepalive loop every 60s (`Migrating data from old database...`)
     - `GRANT postgres TO <awx_user>`
     - `PGPASSWORD=$PGPASSWORD_OLD pg_dump | PGPASSWORD=$POSTGRES_PASSWORD pg_restore`
     - `REVOKE postgres FROM <awx_user>`
5. `PGPASSWORD_OLD` is injected on the managed StatefulSet only when an old secret exists (`postgres.yaml.j2` secretKeyRef on the old configuration secret's `password` key). `POSTGRES_PASSWORD` is the managed superuser password env on that pod.

## Why it is “external → internal only”

The dump side already speaks TCP to an arbitrary host (external or otherwise). The restore side is hard-wired to “whatever postgres is listening inside the pod we exec’d into,” because:

- client tools live in the postgres image, not the operator image
- dest credentials/env are the managed pod’s `POSTGRES_PASSWORD` / local socket defaults

So the limitation is **where the pipe runs**, not an inherent inability of `pg_dump`/`pg_restore` to talk to two external endpoints. Our `playbook.yml` runs that same pipe on a host/EE that has the client tools and passes `-h/-p` on **both** sides.

## Post-`pg_restore` cleanup — is there UUID scrubbing?

**No.** Exhaustive search of `/opt/ansible/roles` on this operator image found **no** task that deletes or rewrites Instance UUIDs (or other primary keys) after `migrate_data.yml`. A full `pg_restore` of the AWX/Controller database keeps old UUIDs/rows intact by design.

What *does* run later in the same reconcile (after Deployments are back and a task pod exists) is application-level init — **not** a UUID purge:

| Step (in `install.yml` order) | File | What it actually does |
|-------------------------------|------|------------------------|
| Django schema migrate | `install.yml` → `awx-manage migrate --noinput` | Schema only; not data UUID cleanup |
| Django init | `initialize_django.yml` | Superuser ensure; **`unregister_queue --queuename=tower`** if a legacy `[tower capacity=…]` group exists (classic Tower → AWX naming); register default EEs; optional preload data |
| Status | `update_status.yml` | Writes `migratedFromSecret` etc. |
| Cleanup | `cleanup.yml` | Clears K8s Secret `ownerReferences` when `garbage_collect_secrets` is false — **cluster objects**, not DB rows |

Related but **not** part of the DB migration path:

- Settings template sets `SYSTEM_UUID = os.environ.get('MY_POD_UID', …)` — new pods register with **new** instance UUIDs on provision; restored DB still has the **old** Instance rows until something removes them.
- Pod **preStop** runs `awx-manage disable_instance --wait` (lifecycle drain), not migrate cleanup.
- Manual/ops tools on the controller image (not invoked by the operator migrate path): `awx-manage list_instances`, `deprovision_instance --hostname …`, `disable_instance`, `unregister_queue`, etc.

So if someone said “there might be cleanup that removes old UUIDs afterward,” that is **not** implemented in this operator’s Ansible roles. Ghost/stale instances after a restore are an expected consequence of restoring Instance rows; cleaning them is a separate `awx-manage deprovision_instance` (or equivalent) step you would add yourself.

Additional files under `_extracted/` from the full tree export (same pod/image): entire `roles/{installer,backup,restore,common}`, `playbooks/`, `watches.yaml`, bundled collections, plus `artifacts/` provenance.

## Related: managed PG major upgrade

`upgrade_postgres.yml` is a sibling stream (`pg_dump` from old in-cluster service → `pg_restore` on the new managed pod) with the same keepalive + GRANT/REVOKE pattern. Kept under `_extracted/` for comparison; not required for external→external.

## What was intentionally not exported

- Operator runner `env/extravars` (may contain cluster/object secrets)
- Artifact `stdout` blobs from prior reconciles (noisy; may echo sensitive module args when `no_log` was false)
- `/opt/ansible/.ansible/tmp` (runtime scratch; excluded from the tar)
- Python `__pycache__` / `*.pyc`
