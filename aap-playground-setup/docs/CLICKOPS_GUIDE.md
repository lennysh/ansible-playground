# Lenny's Ansible Playground — AAP Web UI Setup Guide

Manual steps to create the **seed** AAP objects so you can launch
**Playground | Apply CaC** and bring in (or refresh) all demo job templates.

Inspired by the [APD Clickops Guide](https://github.com/shadowman-lab/AAP-POC-Accelerator/blob/main/docs/APD_CLICKOPS_GUIDE.md).

---

## Prerequisites

- A running Ansible Automation Platform environment (2.5+ recommended)
- Admin (or org-admin) access to the Controller / Platform UI
- Network access from AAP to `https://github.com/lennysh/ansible-playground.git`
- An execution environment that can install `infra.aap_configuration` (default
  EE is fine if Galaxy/Automation Hub is reachable; otherwise pre-bake the
  collection into a custom EE)

---

## Step 1 — Create the Organization

**Access Management → Organizations → Create organization**

| Field | Value |
|---|---|
| Name | `Lenny's Ansible Playground` |
| Description | Ansible demo playground job templates and surveys |
| Galaxy Credentials | Attach **Ansible Galaxy** (see below) |

Click **Save**.

### Galaxy credential (required for project collection sync)

Project updates only install collections from `collections/requirements.yml` /
`aap-playground-setup/collections/requirements.yml` when the **organization**
has at least one Galaxy credential. Without that, sync shows:

```text
Collection and role syncing disabled. Check the AWX_ROLES_ENABLED and
AWX_COLLECTIONS_ENABLED settings and Galaxy credentials on the project's
organization.
```

AAP usually ships a global **Ansible Galaxy** credential (public
`https://galaxy.ansible.com/`, no token required). Attach it to this org:

1. Open **Lenny's Ansible Playground** → **Edit**
2. Under **Galaxy Credentials**, search for and select **Ansible Galaxy**
3. Save

If that credential is missing, create one first:

**Automation Execution → Infrastructure → Credentials → Create credential**

| Field | Value |
|---|---|
| Name | `Ansible Galaxy` |
| Organization | *(leave blank — global — so any org can use it)* |
| Credential Type | `Ansible Galaxy/Automation Hub API Token` |
| Galaxy Server URL | `https://galaxy.ansible.com/` |
| API Token | *(leave blank for anonymous public Galaxy)* |

Then attach it on the organization as above. Order matters if you add multiple
sources later (Hub before public Galaxy, etc.).

`infra.aap_configuration` (used by **Playground | Apply CaC**) is published on
Galaxy, so this step is required for the Setup job’s project sync.

---

## Step 2 — Create the Inventory and localhost host

### 2a — Inventory

**Automation Execution → Infrastructure → Inventories → Create inventory**

| Field | Value |
|---|---|
| Name | `Playground Inventory` |
| Organization | `Lenny's Ansible Playground` |

Click **Save**.

### 2b — Host

Inside **Playground Inventory → Hosts → Create host**:

| Field | Value |
|---|---|
| Name | `localhost` |
| Variables | `ansible_connection: local` |

Click **Save**.

---

## Step 3 — Create the AAP Credential

**Automation Execution → Infrastructure → Credentials → Create credential**

| Field | Value |
|---|---|
| Name | `AAP Credential` |
| Description | Used by Playground \| Apply CaC to create/update Controller objects |
| Organization | `Lenny's Ansible Playground` |
| Credential Type | `Red Hat Ansible Automation Platform` |
| Red Hat Ansible Automation Platform URL | `https://<your-aap-fqdn>` |
| Username | *(admin or org admin)* |
| Password | *(or leave blank and use a token)* |
| OAuth Token | *(optional alternative to username/password)* |
| Verify SSL | Checked in production; uncheck only for lab/self-signed |

Click **Save**.

---

## Step 4 — Create the Project

**Automation Execution → Infrastructure → Projects → Create project**

| Field | Value |
|---|---|
| Name | `Lenny's Ansible Playground` |
| Organization | `Lenny's Ansible Playground` |
| Source Control Type | `Git` |
| Source Control URL | `https://github.com/lennysh/ansible-playground.git` |
| Source Control Branch/Tag/Commit | `main` |
| Options | Check **Update Revision on Launch** so jobs always sync latest `main` before running |

Click **Save**. Wait for the project sync to finish (green status) before continuing.
Confirm the sync job did **not** skip collections (org Galaxy credential must be
set — see Step 1).

---

## Step 5 — Create the Setup Job Template

**Automation Execution → Templates → Create template → Create job template**

| Field | Value |
|---|---|
| Name | `Playground \| Apply CaC` |
| Job Type | `Run` |
| Inventory | `Playground Inventory` |
| Project | `Lenny's Ansible Playground` |
| Playbook | `aap-playground-setup/playbook.yml` |
| Credentials | `AAP Credential` |
| Privilege Escalation | Off |
| Concurrent Jobs | Allowed (optional) |

Click **Save**.

> The Setup JT’s execution environment must be able to resolve
> `infra.aap_configuration` (Galaxy / private Hub, or baked into the image).
> See [`collections/requirements.yml`](../collections/requirements.yml).

### Optional survey — seed credential inputs on first create

After the first successful Apply (or when this survey is present on the seeded
JT), launch prompts for optional values. All questions are optional; leave blank
to skip.

| Question | Variable | Notes |
|---|---|---|
| Machine username | `playground_machine_username` | e.g. `ec2-user` |
| Satellite URL | `playground_satellite_url` | e.g. `https://satellite.example.com` |
| Satellite username | `playground_satellite_username` | |
| Satellite password | `playground_satellite_password` | Password type |
| Red Hat offline token | `playground_offline_token` | Password type; from [access.redhat.com/management/api](https://access.redhat.com/management/api) |
| EE registry prefix | `playground_ee_registry` | e.g. `quay.io/your-ns` |

Blank answers are trimmed and omitted. Values apply only when the credential is
**first created** (`state: exists` skips updates afterward). Prefer filling
credentials in the UI after Apply, or pass overrides on the first launch.

Same vars work from ansible-core via [`extra_vars.example.yml`](../extra_vars.example.yml).
Defined in [`vars/job_templates.yml`](../vars/job_templates.yml).

---

## Step 6 — Launch Setup

Open **Playground | Apply CaC** → **Launch**.

On success, AAP will contain:

- Credential types: `Red Hat Offline Token`, `Red Hat Satellite Server`
- Credential shells: Machine, Satellite, Red Hat Offline Token (fill in the UI)
- Execution environments for Kerberos / WinRM demos
- `Playground Windows Inventory` (empty stub)
- One surveyed job template per demo that ships `playbook-aap.yml`
- The Setup JT itself (kept in sync with CaC)

Re-launch this template anytime after you pull new CaC changes into the project.

---

## After Apply — fill credential shells (UI)

Setup creates credentials with **no placeholder input defaults**. They use
`state: exists`, so re-running CaC will **not** overwrite username, host, or
secrets you set in the UI (`update_secrets: false` is belt-and-suspenders only).

| Credential | What to set |
|---|---|
| **Playground Machine Credential** | SSH key (Linux) and/or UPN + password (Windows / Kerberos) |
| **Playground Satellite Credential** | Satellite URL, username, password |
| **Playground Red Hat Offline Token** | Token from [access.redhat.com/management/api](https://access.redhat.com/management/api) |

To seed on **first create**, use the Setup JT survey (Step 5) or ansible-core
`-e` / [`extra_vars.example.yml`](../extra_vars.example.yml). Blank answers are
ignored. After the credential exists, edit it in the UI (or delete it and
re-run Apply with overrides to recreate).

---

## Final checklist

- [ ] Organization has a **Galaxy credential** attached (e.g. **Ansible Galaxy**)
- [ ] Project sync completed successfully (collections not skipped)
- [ ] `Playground | Apply CaC` completed successfully at least once
- [ ] **Playground Machine Credential** updated with a real SSH key and/or
      Windows UPN + password for managed hosts
- [ ] **Playground Satellite Credential** filled in if you use the Satellite demo
- [ ] **Playground Red Hat Offline Token** filled from
      [access.redhat.com/management/api](https://access.redhat.com/management/api)
      for the collection-download demo
- [ ] Kerberos EE images built and pushed to a registry the controller can pull:
      - `demo-kerberos-winrm-ee:latest` (see `demo-kerberos-winrm/execution-environment.yml`)
      - `demo-winrm-vs-psrp-ee:latest` (see `demo-winrm-vs-psrp/execution-environment.yml`)
  - If images live under a registry prefix, re-run Setup with extra var
    `playground_ee_registry: quay.io/your-ns` (or edit `vars/bootstrap.yml` /
    [`extra_vars.example.yml`](../extra_vars.example.yml))
- [ ] Attach a real **Windows** inventory (group `windows`) to Kerberos / WinRM JTs
- [ ] Attach a customer **installer inventory** to `Demo | AAP Connectivity`
- [ ] Launch a simple localhost demo (e.g. **Demo | AAP Survey PEM Key**) to
      validate end-to-end
