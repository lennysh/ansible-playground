# Clean up AAP 2.4 execution / hop node (RPM)

Host-local “undo” script for an **AAP 2.4 RPM-installed execution or hop node**,
so the same machine (kept for static IP / firewall rules) can be reused with an
**AAP 2.6+ install bundle** (Operator) or a fresh RPM receptor install.

Derived from the AAP 2.4 RPM installer deprovision path:

- `playbooks/uninstall.yml` → `roles/deprovision`
- `roles/deprovision/tasks/receptor.yml`
- `roles/deprovision/defaults/main.yml` (`receptor_cleanup_rpm_list`,
  `receptor_cleanup_files_list`)

## When to use this

- Reusing a RHEL VM that previously ran AAP 2.4 Receptor (execution or hop).
- You cannot (or will not) reimage the OS, but need a clean slate for 2.6+.
- Prefer this over guessing packages/paths by hand.

## When not to use this

- **Controller / Hub / EDA / database** hosts — this script only mirrors
  execution-plane Receptor deprovision, not full `uninstall_controller` /
  postgres wipe.
- If you still have the **2.4** installer and inventory with the host under
  `[execution_nodes]`, the supported path is still:

  ```bash
  ./setup.sh -u -e "uninstall_controller=true" -e "deprovision_disclaimer=false"
  ```

  Use the **2.4** installer for that uninstall (version check against
  `/etc/ansible-automation-platform/VERSION`).

## What it removes

| Category | Items |
|----------|--------|
| Service | Stop/disable `receptor` |
| RPMs | `receptor`, `receptorctl`, `ansible-runner` (+ `dnf autoremove`) |
| Paths | `/etc/receptor`, systemd override dirs, tmpfiles, `/var/lib/receptor`, `/var/lib/awx`, `/tmp/receptor`, `/var/log/receptor`, … |
| Users | `awx`, `receptor` (and linger) |
| Optional | Managed AAP CA anchors under `/etc/pki/ca-trust/...`, `/etc/ansible-automation-platform` |

## What it does **not** remove

- `podman` / `crun` (2.6 execution bundles still need them)
- External firewall / provider egress rules (only optional local firewalld)
- Controller DB / Operator Instance registration (do that in the UI or
  `awx-manage deprovision_instance` on the **control plane**)

## Usage

```bash
cd random/aap-24-execution-hop-cleanup
sudo bash cleanup-aap24-exec-hop.sh
```

Or copy the script to the target host and run as root. Safe to re-run.

Optional steps (firewalld port **27199/tcp**, RHSM 2.4 → 2.6 repos) are
commented in the script — uncomment if needed.

## After cleanup (2.6 Operator install bundle)

1. Confirm FQDN: `hostnamectl` / `hostname -f` (avoid `localhost.localdomain`).
2. In AAP UI: remove any stale Instance for that hostname, **Add** execution/hop
   with the correct FQDN, download a **new** install bundle.
3. Run `install_receptor.yml` from that bundle.
4. Ensure TCP **27199** is open end-to-end to peers (control / hop).

## Related

- Case pattern: reuse 2.4 hop/exec IP on Operator-based 2.6; leftover Receptor
  config/certs/users can confuse a new install bundle.
- KCS examples around mesh wipe / reinstall often include removing
  `/etc/receptor` and re-running the bundle after deprovision on the
  control plane.
