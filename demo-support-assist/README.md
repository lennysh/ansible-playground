# demo-support-assist — Red Hat Support Assist (infra.support_assist)

Wrappers around the [infra.support_assist](https://github.com/redhat-cop/infra.support_assist) collection: gather diagnostics (AAP API dump, OpenShift must-gather, sosreport), optionally **create or update** a Red Hat Support Case, and upload artifacts.

Each flow has a CLI playbook and an AAP twin (`*-aap.yml`). Job templates live in [`aap-playground-setup/vars/job_templates.yml`](../aap-playground-setup/vars/job_templates.yml).

## Prerequisites

| Need | Used by |
|------|---------|
| `infra.support_assist` collection | all |
| Red Hat offline token (`redhat_offline_token` / `REDHAT_OFFLINE_TOKEN`) | case create/update / upload |
| AAP API credential (or `AAP_*` env) | AAP API Gather |
| `oc` on control/EE | OCP Must Gather |
| SSH + become to Linux hosts | SOS Report |
| `curl` on control/EE | case file upload |

```bash
ansible-galaxy collection install -r collections/requirements.yml
export REDHAT_OFFLINE_TOKEN='YOUR_OFFLINE_TOKEN'   # https://access.redhat.com/management/api
```

## Playbooks

| Playbook | Collection entry | Typical inventory |
|----------|------------------|-------------------|
| [`playbook-aap-api-gather.yml`](playbook-aap-api-gather.yml) | `infra.support_assist.aap_api_gather` | localhost |
| [`playbook-ocp-must-gather.yml`](playbook-ocp-must-gather.yml) | `infra.support_assist.ocp_must_gather` | localhost |
| [`playbook-sos-report.yml`](playbook-sos-report.yml) | `infra.support_assist.sos_report` | real Linux hosts |
| [`playbook-rh-case-create.yml`](playbook-rh-case-create.yml) | `infra.support_assist.rh_case_create` | localhost |
| [`playbook-rh-case-update.yml`](playbook-rh-case-update.yml) | roles (survey-friendly builder) | localhost |

**Create vs update:** omit `case_id` and supply create fields (`case_summary`, `case_description`, `case_product`, `case_product_version`, `case_type`, `case_severity`) to create; set `case_id` to update an existing case.

Example vars: [`vars/`](vars/) (`*.example.yml`).

### CLI examples

```bash
# AAP API gather → existing case
ansible-playbook playbook-aap-api-gather.yml -e @vars/aap_api_gather_update.example.yml

# OCP must-gather → new case
ansible-playbook playbook-ocp-must-gather.yml -e @vars/ocp_must_gather_create.example.yml

# SOS report (needs inventory)
cp inventories/hosts.example.yml inventories/hosts.yml   # edit hosts
ansible-playbook -i inventories/hosts.yml playbook-sos-report.yml \
  -e @vars/sos_report_create.example.yml

# Case API only
ansible-playbook playbook-rh-case-create.yml -e @vars/rh_case_create.example.yml
ansible-playbook playbook-rh-case-update.yml -e @vars/rh_case_update.example.yml
```

Gather without upload: `-e upload=false`.

## Ansible Automation Platform

After syncing this project, run **Playground | Apply CaC** to create:

| Job template | Playbook | Credentials |
|--------------|----------|-------------|
| Demo \| Support Assist \| AAP API Gather \| Create Case | `playbook-aap-api-gather-aap.yml` | Hub Offline Token + AAP Credential |
| Demo \| Support Assist \| AAP API Gather \| Update Case | same | same |
| Demo \| Support Assist \| OCP Must Gather \| Create Case | `playbook-ocp-must-gather-aap.yml` | Hub Offline Token |
| Demo \| Support Assist \| OCP Must Gather \| Update Case | same | same |
| Demo \| Support Assist \| SOS Report \| Create Case | `playbook-sos-report-aap.yml` | Hub Offline Token + Machine (ask inventory/limit) |
| Demo \| Support Assist \| SOS Report \| Update Case | same | same |
| Demo \| Support Assist \| RH Case \| Create | `playbook-rh-case-create-aap.yml` | Hub Offline Token |
| Demo \| Support Assist \| RH Case \| Update | `playbook-rh-case-update-aap.yml` | Hub Offline Token |

Offline token is injected as `redhat_offline_token` via the **Playground Hub Offline Token** credential type (same as the collection-download demo). Do not put the token in a survey.

OCP must-gather needs an EE (or control node) with `oc` installed.

## Layout

```text
demo-support-assist/
├── README.md
├── collections/requirements.yml
├── inventories/hosts.example.yml
├── vars/*.example.yml
├── playbook-*-aap.yml          # AAP JT entry points
└── playbook-*.yml              # CLI + shared logic
```

## Event-Driven Ansible + OpenTrashmail

Email → OpenTrashmail webhook → EDA rulebook → these job templates (case create, AAP API gather + create, case update).

See [eda-playground `opentrashmail_support_assist`](https://github.com/lennysh/eda-playground/blob/main/extensions/eda/rulebooks/opentrashmail_support_assist.md) for the rulebook, mailbox conventions, and demo script.

## References

- [infra.support_assist README](https://github.com/redhat-cop/infra.support_assist)
- [Case option lists](https://github.com/redhat-cop/infra.support_assist/blob/devel/roles/rh_case/docs/CASE_OPTIONS.md)
- [Red Hat API tokens](https://access.redhat.com/management/api)
