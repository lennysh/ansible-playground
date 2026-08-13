#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Lenny Shirley and contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vmware_survey_options
short_description: Gather vSphere values for AAP survey single-select options
description:
  - Connects to one or more vCenter servers and builds sorted unique lists used
    as AAP Job Template survey choices.
  - C(vsphere_destination) — C(hostname / datacenter / cluster).
  - C(vsphere_datastore) — C([NAME]) for datastore clusters (StoragePod) and,
    by default, standalone datastores (not members of a StoragePod). Labs
    without SDRS still get bracketed datastore names for survey choices.
  - C(vsphere_folder) — C(hostname/datacenter/folder) under VM and Templates
    (nested segments joined with C(/)).
  - C(vsphere_portgroup) — network portgroup names (standard and distributed;
    uplink portgroups skipped).
options:
  hostname:
    description:
      - Single vCenter hostname or IP. Mutually exclusive with I(vcenters).
    type: str
  vcenters:
    description:
      - List of vCenter hostnames/IPs (or dicts with C(hostname) and optional
        per-vCenter C(username)/C(password)/C(port)/C(validate_certs)).
      - Mutually exclusive with I(hostname).
    type: list
    elements: raw
  username:
    description:
      - Default vCenter username (overridable per entry in I(vcenters)).
    type: str
    required: true
  password:
    description:
      - Default vCenter password (overridable per entry in I(vcenters)).
    type: str
    required: true
    no_log: true
  port:
    description: vCenter HTTPS port.
    type: int
    default: 443
  validate_certs:
    description: Verify TLS certificates when connecting to vCenter.
    type: bool
    default: true
  include_nested_vm_folders:
    description:
      - When true, include nested folders under VM and Templates (path segments
        joined with C(/)). When false, only immediate children of each
        datacenter VM folder.
    type: bool
    default: true
  vsphere_datastore_mode:
    description:
      - What to put in C(vsphere_datastore) (always formatted as C([NAME])).
      - C(pods) — only StoragePod / datastore clusters.
      - C(datastores) — only Datastore objects (every datastore).
      - C(both) — StoragePods plus standalone datastores (parent is not a
        StoragePod). Default; useful when a lab has no SDRS clusters.
    type: str
    choices: [pods, datastores, both]
    default: both
author:
  - Lenny Shirley (@lennysh)
"""

EXAMPLES = r"""
- name: Gather survey options from several vCenters (shared credentials)
  vmware_survey_options:
    vcenters:
      - vcsa01.lab.example
      - vcsa02.lab.example
    username: "{{ vmware_username }}"
    password: "{{ vmware_password }}"
    validate_certs: false
  register: survey_opts
"""

RETURN = r"""
vsphere_destination:
  description: Sorted list of C(hostname / datacenter / cluster) strings.
  returned: always
  type: list
  elements: str
vsphere_datastore:
  description: >-
    Sorted list of C([name]) strings for StoragePods and (optionally)
    standalone datastores.
  returned: always
  type: list
  elements: str
vsphere_folder:
  description: Sorted list of C(hostname/datacenter/folder) strings.
  returned: always
  type: list
  elements: str
vsphere_portgroup:
  description: Sorted list of portgroup names.
  returned: always
  type: list
  elements: str
vcenters:
  description: Per-vCenter gather summary (counts and errors).
  returned: always
  type: list
  elements: dict
"""

import ssl
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

PYVMOMI_IMP_ERR = None
try:
    from pyVim.connect import Disconnect, SmartConnect
    from pyVmomi import vim

    HAS_PYVMOMI = True
except ImportError:
    HAS_PYVMOMI = False
    PYVMOMI_IMP_ERR = traceback.format_exc()
    vim = None  # type: ignore[assignment]


def _normalize_hostname(raw):
    host = (raw or "").strip()
    for prefix in ("https://", "http://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix) :]
    return host.rstrip("/")


def _normalize_vcenter_entries(module):
    hostname = module.params.get("hostname")
    vcenters = module.params.get("vcenters") or []

    if hostname and vcenters:
        module.fail_json(msg="Specify either hostname or vcenters, not both.")
    if not hostname and not vcenters:
        module.fail_json(msg="Provide hostname or a non-empty vcenters list.")

    entries = []
    sources = [{"hostname": hostname}] if hostname else vcenters
    for item in sources:
        if isinstance(item, dict):
            entry_host = item.get("hostname") or item.get("host") or item.get("name")
            if not entry_host:
                module.fail_json(
                    msg="Each vcenters dict entry needs hostname (or host/name)."
                )
            entries.append(
                {
                    "hostname": _normalize_hostname(entry_host),
                    "username": item.get("username") or module.params["username"],
                    "password": item.get("password") or module.params["password"],
                    "port": int(item.get("port") or module.params["port"]),
                    "validate_certs": (
                        item["validate_certs"]
                        if "validate_certs" in item
                        else module.params["validate_certs"]
                    ),
                }
            )
        else:
            entries.append(
                {
                    "hostname": _normalize_hostname(str(item)),
                    "username": module.params["username"],
                    "password": module.params["password"],
                    "port": int(module.params["port"]),
                    "validate_certs": module.params["validate_certs"],
                }
            )

    cleaned = [e for e in entries if e["hostname"]]
    if not cleaned:
        module.fail_json(msg="No usable vCenter hostnames after normalization.")
    return cleaned


def _connect(entry):
    context = None
    if not entry["validate_certs"]:
        context = ssl._create_unverified_context()
    return SmartConnect(
        host=entry["hostname"],
        user=entry["username"],
        pwd=entry["password"],
        port=entry["port"],
        sslContext=context,
    )


def _walk_vsphere_folders(folder, prefix_parts, include_nested):
    """Yield (path_parts) for VM folders under the datacenter vmFolder."""
    for child in getattr(folder, "childEntity", []) or []:
        if not isinstance(child, vim.Folder):
            continue
        parts = prefix_parts + [child.name]
        yield parts
        if include_nested:
            for nested in _walk_vsphere_folders(child, parts, include_nested):
                yield nested


def _container_view(content, vimtype):
    view = content.viewManager.CreateContainerView(content.rootFolder, [vimtype], True)
    try:
        return list(view.view)
    finally:
        view.Destroy()


def _iter_compute_clusters(folder):
    for child in getattr(folder, "childEntity", []) or []:
        if isinstance(child, vim.ClusterComputeResource):
            yield child
        elif isinstance(child, vim.Folder):
            for nested in _iter_compute_clusters(child):
                yield nested
        elif isinstance(child, vim.ComputeResource) and not isinstance(
            child, vim.ClusterComputeResource
        ):
            # Standalone host ComputeResource — skip for cluster destinations
            continue


def _is_uplink_portgroup(network):
    if not isinstance(network, vim.dvs.DistributedVirtualPortgroup):
        return False
    name = network.name or ""
    if name.startswith("DVUplinks") or "DVUplinks-" in name:
        return True
    config = getattr(network, "config", None)
    if config is not None and getattr(config, "uplink", False):
        return True
    return False


def _gather_datastore_choices(content, mode):
    """Return set of [name] strings for survey vsphere_datastore choices."""
    choices = set()
    mode = (mode or "both").lower()

    if mode in ("pods", "both"):
        for pod in _container_view(content, vim.StoragePod):
            name = (getattr(pod, "name", None) or "").strip()
            if name:
                choices.add("[{0}]".format(name))

    if mode == "pods":
        return choices

    for datastore in _container_view(content, vim.Datastore):
        # In "both" mode, skip members of a StoragePod — the pod is listed.
        if mode == "both" and isinstance(
            getattr(datastore, "parent", None), vim.StoragePod
        ):
            continue
        name = (getattr(datastore, "name", None) or "").strip()
        if name:
            choices.add("[{0}]".format(name))
    return choices


def _gather_one(entry, include_nested_vm_folders, vsphere_datastore_mode):
    si = _connect(entry)
    try:
        content = si.RetrieveContent()
        vcenter = entry["hostname"]
        destinations = set()
        folders = set()
        portgroups = set()

        for datacenter in content.rootFolder.childEntity:
            if not isinstance(datacenter, vim.Datacenter):
                continue
            dc_name = datacenter.name

            for cluster in _iter_compute_clusters(datacenter.hostFolder):
                destinations.add(
                    "{0} / {1} / {2}".format(vcenter, dc_name, cluster.name)
                )

            for path_parts in _walk_vsphere_folders(
                datacenter.vmFolder, [], include_nested_vm_folders
            ):
                rel = "/".join(path_parts)
                folders.add("{0}/{1}/{2}".format(vcenter, dc_name, rel))

            for network in getattr(datacenter, "network", []) or []:
                if _is_uplink_portgroup(network):
                    continue
                name = (getattr(network, "name", None) or "").strip()
                if name:
                    portgroups.add(name)

        vsphere_datastores = _gather_datastore_choices(
            content, vsphere_datastore_mode
        )

        return {
            "hostname": vcenter,
            "ok": True,
            "error": None,
            "vsphere_destination": sorted(destinations),
            "vsphere_datastore": sorted(vsphere_datastores),
            "vsphere_folder": sorted(folders),
            "vsphere_portgroup": sorted(portgroups),
            "counts": {
                "vsphere_destination": len(destinations),
                "vsphere_datastore": len(vsphere_datastores),
                "vsphere_folder": len(folders),
                "vsphere_portgroup": len(portgroups),
            },
        }
    finally:
        try:
            Disconnect(si)
        except Exception:
            pass


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type="str"),
            vcenters=dict(type="list", elements="raw"),
            username=dict(type="str", required=True),
            password=dict(type="str", required=True, no_log=True),
            port=dict(type="int", default=443),
            validate_certs=dict(type="bool", default=True),
            include_nested_vm_folders=dict(type="bool", default=True),
            vsphere_datastore_mode=dict(
                type="str",
                default="both",
                choices=["pods", "datastores", "both"],
            ),
        ),
        supports_check_mode=True,
        mutually_exclusive=[("hostname", "vcenters")],
        required_one_of=[("hostname", "vcenters")],
    )

    if not HAS_PYVMOMI:
        module.fail_json(
            msg=missing_required_lib("pyvmomi"),
            exception=PYVMOMI_IMP_ERR,
        )

    entries = _normalize_vcenter_entries(module)
    include_nested = module.params["include_nested_vm_folders"]
    ds_mode = module.params["vsphere_datastore_mode"]

    all_destination = set()
    all_datastore = set()
    all_folder = set()
    all_portgroup = set()
    summaries = []
    errors = []

    for entry in entries:
        try:
            result = _gather_one(entry, include_nested, ds_mode)
        except Exception as exc:
            err = {
                "hostname": entry["hostname"],
                "ok": False,
                "error": str(exc),
                "counts": {
                    "vsphere_destination": 0,
                    "vsphere_datastore": 0,
                    "vsphere_folder": 0,
                    "vsphere_portgroup": 0,
                },
            }
            summaries.append(err)
            errors.append("{0}: {1}".format(entry["hostname"], exc))
            continue

        summaries.append(
            {
                "hostname": result["hostname"],
                "ok": True,
                "error": None,
                "counts": result["counts"],
            }
        )
        all_destination.update(result["vsphere_destination"])
        all_datastore.update(result["vsphere_datastore"])
        all_folder.update(result["vsphere_folder"])
        all_portgroup.update(result["vsphere_portgroup"])

    if errors and not (
        all_destination or all_datastore or all_folder or all_portgroup
    ):
        module.fail_json(
            msg="Failed to gather from every vCenter: {0}".format("; ".join(errors)),
            vcenters=summaries,
            vsphere_destination=[],
            vsphere_datastore=[],
            vsphere_folder=[],
            vsphere_portgroup=[],
        )

    module.exit_json(
        changed=False,
        vsphere_destination=sorted(all_destination),
        vsphere_datastore=sorted(all_datastore),
        vsphere_folder=sorted(all_folder),
        vsphere_portgroup=sorted(all_portgroup),
        vcenters=summaries,
        warnings=(
            ["Partial gather; some vCenters failed: {0}".format("; ".join(errors))]
            if errors
            else []
        ),
    )


if __name__ == "__main__":
    main()
