# demo-dynamic-inventory — AAP inventory source YAML catalog

One-stop set of **YAML inventory plugin** examples you can point an AAP inventory
source at (Sourced from a Project), or pass with `ansible-inventory -i …`.

These are **templates**: copy a file, adjust filters/regions/paths, attach the
matching AAP credential, and sync. Do not commit real hostnames, usernames, or
passwords.

> Inventory-plugin-only demo — no Job Template / CaC entry.

## Files

| File | Plugin | Required filename suffix | Typical AAP credential |
|------|--------|--------------------------|------------------------|
| [`example.vmware_vms.yml`](example.vmware_vms.yml) | `vmware.vmware.vms` | `vms.yml` / `vmware_vms.yml` | VMware vCenter |
| [`example.vmware_vm_inventory.yml`](example.vmware_vm_inventory.yml) | `community.vmware.vmware_vm_inventory` | `vmware.yml` / `vmware_vm_inventory.yml` | VMware vCenter (legacy; prefer `vms`) |
| [`example.aws_ec2.yml`](example.aws_ec2.yml) | `amazon.aws.aws_ec2` | `aws_ec2.yml` | Amazon Web Services |
| [`example.azure_rm.yml`](example.azure_rm.yml) | `azure.azcollection.azure_rm` | `azure_rm.yml` | Microsoft Azure Resource Manager |
| [`example.gcp_compute.yml`](example.gcp_compute.yml) | `google.cloud.gcp_compute` | `gcp_compute.yml` / `gcp.yml` | Google Compute Engine |
| [`example.foreman.yml`](example.foreman.yml) | `redhat.satellite.foreman` | `foreman.yml` | Red Hat Satellite |
| [`example.proxmox.yml`](example.proxmox.yml) | `community.proxmox.proxmox` | `.proxmox.yml` | Custom / env (`PROXMOX_*`) |
| [`example.openstack.yml`](example.openstack.yml) | `openstack.cloud.openstack` | `openstack.yml` | OpenStack |
| [`example.constructed.yml`](example.constructed.yml) | `ansible.builtin.constructed` | `.yml` (second source) | None (reshapes another source) |

Related demos elsewhere in this repo:

- [`demo-dynamic-inventory-with-static-vars`](../demo-dynamic-inventory-with-static-vars/) — Proxmox + `group_vars` / `host_vars`
- [`demo-dynamic-inventory-merge`](../demo-dynamic-inventory-merge/) — custom merge of flat INI/YAML/JSON
- [`demo-dynamic-inventory-csv`](../demo-dynamic-inventory-csv/) — CSV-driven inventory plugin

## AAP usage

1. Add this git repo (or a fork) as an AAP **Project**; sync it.
2. Create an **Inventory**.
3. **Sources → Add → Sourced from a Project**
   - Project: this repo
   - Source path: e.g. `demo-dynamic-inventory/example.aws_ec2.yml`
4. Attach the credential for that cloud / vCenter / Satellite.
5. Sync the source; verify hosts/groups under the inventory.

Credentials inject connection details via environment variables (for example
`VMWARE_HOST`, `AWS_*`, `FOREMAN_*`). Leave secrets out of the YAML.

### Filename suffixes matter

Ansible’s `auto` inventory plugin selects the implementation from the **file
name suffix** as well as the `plugin:` line. Keep the required ending when you
rename copies (for example `prod-east.aws_ec2.yml`).

### Pairing with `constructed`

Add `example.constructed.yml` as a **second** inventory source (same inventory,
higher/lower order as needed) to build cross-cutting groups from hostvars that
the primary plugin already set (`infrastructure_provider`, connection type, …).

## CLI smoke test

```bash
cd demo-dynamic-inventory

# After exporting provider credentials / env vars:
ansible-inventory -i example.aws_ec2.yml --graph
ansible-inventory -i example.vmware_vms.yml --list | head
```

Collections must be present on the controller or in the execution environment
(`amazon.aws`, `azure.azcollection`, `vmware.vmware`, `redhat.satellite`, …).

## Customizing the VMware examples

Both VMware files demonstrate patterns customers often need:

- Prefer a management subnet IP via `compose.ansible_host` + Jinja `select('match', …)`
- Auto-set **PSRP / WinRM** connection vars when `guestId` looks like Windows
- `keyed_groups` from guest OS / tags
- Client-side filters (legacy) or `filter_expressions` / `search_paths` (new plugin)

Start from [`example.vmware_vms.yml`](example.vmware_vms.yml) for new work;
[`example.vmware_vm_inventory.yml`](example.vmware_vm_inventory.yml) remains for
environments still on `community.vmware`.

## Sanitizing lab hostnames

Before committing lab-specific inventory YAML, rely on the repo pre-commit hook
(`scripts/sanitize-strings.sh`). Copy
[`scripts/sanitize-strings.conf.example`](../scripts/sanitize-strings.conf.example)
to `scripts/sanitize-strings.conf` (gitignored) and keep old→new pairs for
internal hostnames and domains.
