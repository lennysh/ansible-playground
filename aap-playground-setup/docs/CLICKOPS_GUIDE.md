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

Click **Save**.

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

---

## Step 6 — Launch Setup

Open **Playground | Apply CaC** → **Launch**.

On success, AAP will contain:

- Credential types: `Red Hat Offline Token`, `Red Hat Satellite Server`
- Placeholder credentials: Machine, Satellite, Hub Offline Token
- Execution environments for Kerberos / WinRM demos
- `Playground Windows Inventory` (empty stub)
- One surveyed job template per demo that ships `playbook-aap.yml`
- The Setup JT itself (kept in sync with CaC)

Re-launch this template anytime after you pull new CaC changes into the project.

---

## Final checklist

- [ ] Project sync completed successfully
- [ ] `Playground | Apply CaC` completed successfully at least once
- [ ] **Playground Machine Credential** updated with a real SSH key and/or
      Windows UPN + password for managed hosts
- [ ] **Playground Satellite Credential** filled in if you use the Satellite demo
- [ ] **Playground Hub Offline Token** filled from
      [access.redhat.com/management/api](https://access.redhat.com/management/api)
      for the collection-download demo
- [ ] Kerberos EE images built and pushed to a registry the controller can pull:
      - `demo-kerberos-winrm-ee:latest` (see `demo-kerberos-winrm/execution-environment.yml`)
      - `demo-winrm-vs-psrp-ee:latest` (see `demo-winrm-vs-psrp/execution-environment.yml`)
  - If images live under a registry prefix, re-run Setup with extra var
    `playground_ee_registry: quay.io/your-ns` (or edit `vars/bootstrap.yml`)
- [ ] Attach a real **Windows** inventory (group `windows`) to Kerberos / WinRM JTs
- [ ] Attach a customer **installer inventory** to `Demo | AAP Connectivity`
- [ ] Launch a simple localhost demo (e.g. **Demo | AAP Survey PEM Key**) to
      validate end-to-end
