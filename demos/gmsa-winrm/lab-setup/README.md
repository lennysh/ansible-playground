# Active Directory lab for demos/gmsa-winrm

This folder contains scripts to build a **minimal domain from scratch** when you do not already have Windows infrastructure.

## What you need

| Item | Minimum |
|------|---------|
| Hypervisor | Hyper-V, VMware Workstation/Fusion, Proxmox, or a cloud VM |
| Windows Server | **One** VM — 2019 or 2022 evaluation ([Microsoft evaluation center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2022)) |
| RAM | 4 GB (8 GB comfortable) |
| Disk | 60 GB |
| Linux host | Fedora/RHEL with `podman` + `ansible-navigator` for running the demo |

The single-VM design makes the DC **also** the WinRM target. That is fine for learning; production would separate roles.

## Network checklist

Before running the script:

1. Set a **static IP** on the Windows VM (or DHCP reservation).
2. Set the VM hostname (e.g. `DC01`).
3. Ensure your Linux host can reach the VM on **TCP 389** (LDAP) and **TCP 5985** (WinRM HTTP).
4. Point the Windows VM DNS at **itself** (127.0.0.1) after promotion, or at the static IP.

## Step 1 — Create the domain and gMSA

On the Windows Server VM, open **PowerShell as Administrator**:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd C:\path\to\ansible-playground\demos/gmsa-winrm\lab-setup
.\Configure-GmsaLab.ps1 -DomainName example.com
```

**The script runs in two phases.** The first execution promotes the server to a domain controller and **reboots**. Run the **same command again** after the reboot to create the gMSA, lookup user, and WinRM settings. Passwords are saved to `C:\Configure-GmsaLab.state.json`.

The script will:

- Install AD DS and promote the server to `example.com` / `EXAMPLE.COM`
- Create KDS root key (lab shortcut: effective immediately)
- Create group `gMSA Password Readers`
- Create user `svc-gmsa-lookup` and add it to that group
- Create gMSA `gmsa-ansible$` allowed for the group to read `msDS-ManagedPassword`
- Add the gMSA to `Remote Management Users`
- Enable WinRM on HTTP (5985) for lab simplicity

**Save the generated passwords** printed to the console.

Reboot the VM if prompted, then verify:

```powershell
Get-ADServiceAccount gmsa-ansible -Properties PrincipalsAllowedToRetrieveManagedPassword
Test-WSMan localhost
```

## Step 2 — DNS from Linux

Your Linux controller/EE must resolve the DC hostname. Add to `/etc/hosts` if you have no lab DNS:

```text
192.0.2.10  dc01.example.com  dc01
```

Replace `192.0.2.10` with your VM IP.

Verify from Linux:

```bash
dig +short _ldap._tcp.example.com SRV
nc -zv dc01.example.com 389
nc -zv dc01.example.com 5985
```

## Step 3 — Configure the demo vars

```bash
cd demos/gmsa-winrm
cp vars/gmsa.example.yml vars/gmsa.yml
cp inventories/hosts.example.yml inventories/hosts.yml
```

Edit `vars/gmsa.yml` using the values printed by `Configure-GmsaLab.ps1`.

Edit `inventories/hosts.yml`:

```yaml
all:
  children:
    windows:
      hosts:
        dc01.example.com:
          ansible_host: dc01.example.com
```

## Step 4 — Build the execution environment

```bash
cd demos/gmsa-winrm
podman login registry.redhat.io   # if using ee-minimal base image
ansible-builder build -f execution-environment.yml -t localhost/demo-gmsa-winrm-ee:latest
```

## Step 5 — Run the demo

```bash
ansible-navigator run playbook-simple.yml -e @vars/gmsa.yml
```

Expected flow:

1. LDAP bind as `svc-gmsa-lookup`
2. Read `msDS-ManagedPassword` for `gmsa-ansible$`
3. Derive NT hash → WinRM NTLM auth as `gmsa-ansible$@EXAMPLE.COM`
4. `win_ping` succeeds
5. `whoami` shows `example\gmsa-ansible$`

Full demo with summary report:

```bash
ansible-navigator run playbook.yml -e @vars/gmsa.yml
```

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `msDS-ManagedPassword is empty` | Lookup user not in `PrincipalsAllowedToRetrieveManagedPassword` |
| LDAP bind failed | Wrong password, firewall on 389, or need `--start-tls` |
| WinRM auth failed | gMSA not in `Remote Management Users`; WinRM not enabled |
| `Access is denied` on WinRM | Unencrypted WinRM disabled — script enables it for lab; check `winrm get winrm/config/service` |
| Cannot resolve DC | Fix `/etc/hosts` or DNS SRV records |

### LDAPS / StartTLS

If your DC requires encryption on LDAP, set in `vars/gmsa.yml`:

```yaml
gmsa_ldap_start_tls: true
# or for LDAPS:
gmsa_ldap_use_ssl: true
gmsa_ldap_port: 636
```

### Test password retrieval alone

Inside the EE container:

```bash
python3 roles/gmsa_winrm/files/fetch_gmsa_password.py \
  --server dc01.example.com \
  --domain EXAMPLE \
  --username svc-gmsa-lookup \
  --password 'YOUR_PASSWORD' \
  --search-base DC=example,DC=com \
  --sam-account-name gmsa-ansible \
  --realm EXAMPLE.COM
```

Success prints JSON with `"success": true`.

## Two-VM layout (optional)

For a more realistic topology:

1. **DC01** — domain controller only (run `Configure-GmsaLab.ps1`)
2. **WIN01** — member server joined to the domain

On WIN01:

```powershell
Add-Computer -DomainName example.com -Credential (Get-Credential) -Restart
# After reboot:
Enable-PSRemoting -Force
Add-ADGroupMember -Identity 'Remote Management Users' -Members 'gmsa-ansible$'
```

Point `inventories/hosts.yml` at `win01.example.com` instead of the DC.

## Security notes

This lab intentionally uses **HTTP WinRM (5985)** and **plain LDAP (389)** for simplicity. Do not expose these settings to production networks. The lookup account can read gMSA secrets — grant that right only where needed.
