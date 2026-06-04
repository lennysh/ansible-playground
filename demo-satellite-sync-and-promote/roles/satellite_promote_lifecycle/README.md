# satellite_promote_lifecycle role

Promotes a Content View version **one lifecycle hop** based on `satellite_promote_target` (must match `satellite_lifecycle_dev`, `_qa`, or `_prod`).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `satellite_workflow_step` | `upstream` | `upstream` or `promote` (set at play level) |
| `satellite_promote_target` | `{{ satellite_lifecycle_dev }}` | LE to promote into (resolved in play `set_fact`) |
| `satellite_lifecycle_promotion_steps` | see `defaults/main.yml` | Maps target → source + path |
| `satellite_promote_to_dev` | `true` | Upstream only: skip role when false |

## CLI examples

```bash
# Library → DEV (with sync/publish in playbook)
ansible-playbook playbook.yml

# DEV → QA after validation
ansible-playbook playbook.yml \
  -e satellite_workflow_step=promote \
  -e satellite_promote_target=QA

# QA → PROD
ansible-playbook playbook.yml \
  -e satellite_workflow_step=promote \
  -e satellite_promote_target=PROD
```

`satellite_promote_target` must match the strings in `satellite_lifecycle_*` vars exactly.
