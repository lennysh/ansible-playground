#!/bin/bash
# Undo AAP 2.4 RPM execution/hop node bits
# (derived from ansible.automation_platform_installer deprovision role)
#
# Run as root on the RHEL host before a fresh AAP 2.6 (or later) install-bundle
# or RPM reinstall. Safe to re-run.
#
# See README.md in this directory for context, scope, and post-cleanup steps.
set -euo pipefail

echo "=== Pre-check (optional inventory of leftovers) ==="
hostname -f
rpm -qa 'receptor*' 'ansible-runner*' 'automation-controller*' 2>/dev/null || true
systemctl status receptor --no-pager -l || true
ls -la /etc/receptor /etc/systemd/system/receptor.service.d \
  /usr/lib/systemd/system/receptor.service.d 2>/dev/null || true

echo "=== 1) Stop / disable Receptor ==="
systemctl stop receptor 2>/dev/null || true
systemctl disable receptor 2>/dev/null || true

echo "=== 2) Remove Receptor-related RPMs (deprovision receptor_cleanup_rpm_list) ==="
# Same packages the installer removes: receptor, receptorctl, ansible-runner
dnf remove -y receptor receptorctl ansible-runner || true
dnf autoremove -y || true

# If anything receptor-related remains:
# rpm -qa | grep -E 'receptor|ansible-runner' ; dnf remove -y <pkg>

echo "=== 3) Remove config / runtime paths (receptor_cleanup_files_list) ==="
rm -rf \
  /etc/security/limits.d/awx.conf \
  /etc/systemd/system/receptor.service.d \
  /etc/receptor \
  /etc/tmpfiles.d/awx-receptor.conf \
  /etc/tmpfiles.d/receptor.conf \
  /tmp/receptor \
  /var/run/receptor \
  /run/receptor \
  /var/run/awx-receptor \
  /run/awx-receptor \
  /var/lib/receptor \
  /var/lib/awx

# Not in the installer list, but often present and should not survive a wipe:
rm -rf /var/log/receptor

# Drop-ins under /usr/lib are owned by the receptor RPM; after dnf remove they should be gone.
# If a stray remains, remove it:
rm -rf /usr/lib/systemd/system/receptor.service.d

systemctl daemon-reload
systemd-tmpfiles --remove /etc/tmpfiles.d/awx-receptor.conf 2>/dev/null || true
systemd-tmpfiles --remove /etc/tmpfiles.d/receptor.conf 2>/dev/null || true

echo "=== 4) Remove users created for mesh (deprovision receptor.yml) ==="
# Installer removes awx only for hosts in [execution_nodes] (includes hop + execution).
loginctl disable-linger awx 2>/dev/null || true
loginctl disable-linger receptor 2>/dev/null || true
userdel -r awx 2>/dev/null || true
userdel -r receptor 2>/dev/null || true
groupdel awx 2>/dev/null || true
groupdel receptor 2>/dev/null || true

echo "=== 5) Optional: managed AAP CA trust bits (certificate_authority deprovision) ==="
# Only if this host ever got the managed/custom AAP CA anchors from the RPM installer:
rm -f \
  /etc/pki/ca-trust/source/anchors/ansible-automation-platform-managed-ca-cert.crt \
  /etc/pki/ca-trust/source/anchors/ansible-automation-platform-custom-ca-cert.crt
rm -rf /etc/ansible-automation-platform
update-ca-trust 2>/dev/null || true

echo "=== 6) Optional: local firewalld rules for Receptor listener (default 27199/tcp) ==="
# Skip if firewalls are managed externally (common). Uncomment to clear local rules:
# PORT=27199
# firewall-cmd --permanent --remove-port=${PORT}/tcp 2>/dev/null || true
# firewall-cmd --reload 2>/dev/null || true

echo "=== 7) Optional: leave AAP 2.4 content repo; enable 2.6 before reinstall ==="
# subscription-manager repos --disable='ansible-automation-platform-2.4-for-rhel-9-*-rpms' || true
# subscription-manager repos --enable='ansible-automation-platform-2.6-for-rhel-9-*-rpms' || true

echo "=== Post-check (expect empty / not found) ==="
rpm -qa 'receptor*' 'ansible-runner*' || true
test ! -e /etc/receptor && echo "OK: /etc/receptor gone"
test ! -e /var/lib/receptor && echo "OK: /var/lib/receptor gone"
id awx 2>&1 || echo "OK: awx user gone"
id receptor 2>&1 || echo "OK: receptor user gone"
systemctl daemon-reload
echo "Cleanup complete. Reboot optional but useful before the 2.6 install bundle."
