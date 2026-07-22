#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Lenny Shirley and contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: aap_project_sync_collections
short_description: Inspect collections installed during AAP project syncs
description:
  - Targets AAP 2.5+ Platform Gateway and queries the Controller API via
    C(/api/controller/v2) for project updates (SCM syncs).
  - Parses ansible-galaxy collection install output from job events.
  - Reports collection name, version, download URL / source host,
    and related install lines (dependencies resolved via requirements).
  - Can discover every project or limit to a named list.
options:
  aap_hostname:
    description:
      - Base URL of the AAP Platform Gateway (for example https://aap.example.com).
      - Falls back to C(AAP_HOSTNAME), then C(CONTROLLER_HOST) (credential inject).
    type: str
  aap_token:
    description:
      - OAuth / personal access token for Gateway.
      - Falls back to C(AAP_TOKEN), then C(CONTROLLER_OAUTH_TOKEN) (credential inject).
    type: str
    no_log: true
  aap_username:
    description:
      - Username for basic auth when no token is set.
      - Falls back to C(AAP_USERNAME), then C(CONTROLLER_USERNAME).
    type: str
  aap_password:
    description:
      - Password for basic auth when no token is set.
      - Falls back to C(AAP_PASSWORD), then C(CONTROLLER_PASSWORD).
    type: str
    no_log: true
  aap_validate_certs:
    description:
      - Verify TLS certificates when talking to the Gateway API.
      - Falls back to C(AAP_VALIDATE_CERTS), then C(CONTROLLER_VERIFY_SSL).
    type: bool
  project_names:
    description:
      - Project names to inspect. Empty list means discover all projects
        (optionally filtered by I(organization)).
    type: list
    elements: str
    default: []
  organization:
    description:
      - Limit discovery to projects in this organization name.
    type: str
  since_hours:
    description:
      - Only consider project updates created within this many hours.
      - Use C(0) to take the latest successful update regardless of age.
    type: int
    default: 168
  updates_per_project:
    description:
      - How many recent successful updates to inspect per project (newest first).
    type: int
    default: 1
  update_status:
    description:
      - Project update status filter.
    type: str
    default: successful
  include_raw_stdout:
    description:
      - Include concatenated galaxy/collection event stdout on each update result.
    type: bool
    default: false
author:
  - Lenny Shirley (@lennysh)
"""

EXAMPLES = r"""
- name: Report collections from every project sync in the last 7 days
  aap_project_sync_collections:
    since_hours: 168
  register: sync_report

- name: Target specific projects
  aap_project_sync_collections:
    project_names:
      - Lenny's Ansible Playground
      - Demo Network Collections
    since_hours: 0
    updates_per_project: 2
  register: sync_report
"""

RETURN = r"""
projects:
  description: Per-project sync inspection results.
  returned: always
  type: list
  elements: dict
summary:
  description: Aggregated counts and unique collections across the report.
  returned: always
  type: dict
aap_hostname:
  description: Gateway base URL used to build UI links in reports.
  returned: always
  type: str
"""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url, open_url

try:
    from ansible.module_utils.common.text.converters import to_native, to_text
except ImportError:  # pragma: no cover - older ansible-core
    from ansible.module_utils._text import to_native, to_text

RE_INSTALLING = re.compile(
    r"Installing '([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+):([^']+)'"
)
RE_DOWNLOADING = re.compile(r"Downloading (https?://\S+)\s+to\s+")
RE_OBTAINED = re.compile(
    r"'([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+):([^']+)'\s+obtained from server\s+(\S+)"
)
RE_INSTALLED_OK = re.compile(
    r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\s+\(([^)]+)\)\s+was installed successfully"
)
RE_TARBALL = re.compile(
    r"/([a-zA-Z0-9_]+)-([a-zA-Z0-9_]+)-([0-9][^/]*?)\.tar\.gz"
)
RE_DEP_MAP = re.compile(r"Process install dependency map", re.IGNORECASE)
# ansible-galaxy git installs: mkdtemp(prefix=repo_basename) then "Cloning into '...'"
RE_CLONING = re.compile(
    r"Cloning into '[^']*?/([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)[^'/]*'"
)
RE_CREATED_COLLECTION = re.compile(
    r"Created collection for ([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)(?::(\S+))?\s+at\s+"
)
RE_GIT_URL = re.compile(
    r"(?:git\+)?(https?://[^\s'\"<>]+?\.git)|"
    r"(git@[^\s'\"<>]+?\.git)"
)

# AAP 2.5+ Platform Gateway path for Automation Controller resources.
GATEWAY_CONTROLLER_API = "/api/controller/v2"


def _env_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _env_bool(default: bool, *names: str) -> bool:
    raw = _env_first(*names)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class ApiClient:
    """Minimal AAP Gateway (/api/controller/v2) REST client with pagination."""

    def __init__(
        self,
        module: AnsibleModule,
        base_url: str,
        token: Optional[str],
        username: Optional[str],
        password: Optional[str],
        validate_certs: bool,
        api_prefix: str = GATEWAY_CONTROLLER_API,
    ):
        self.module = module
        self.base = base_url.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
        self.validate_certs = validate_certs
        self.api_prefix = api_prefix.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer %s" % self.token
        return headers

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return "%s%s" % (self.base, path)

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        fail_on_error: bool = True,
    ) -> Optional[Dict[str, Any]]:
        url = self._url(path)
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                sep = "&" if "?" in url else "?"
                url = "%s%s%s" % (url, sep, urlencode(filtered))

        err = None
        if self.token:
            response, info = fetch_url(
                self.module,
                url,
                headers=self._headers(),
                method="GET",
                timeout=60,
            )
            status = int(info.get("status", 0) or 0)
            if status >= 400 or response is None:
                err = "HTTP %s %s" % (status, info.get("msg", ""))
            else:
                body = response.read()
                return self.module.from_json(to_text(body))
        else:
            try:
                raw = open_url(
                    url,
                    method="GET",
                    headers=self._headers(),
                    url_username=self.username,
                    url_password=self.password,
                    force_basic_auth=True,
                    validate_certs=self.validate_certs,
                    timeout=60,
                )
                return self.module.from_json(to_text(raw.read()))
            except Exception as exc:  # noqa: BLE001 - surface API errors cleanly
                err = to_native(exc)

        if fail_on_error:
            self.module.fail_json(
                msg="AAP Gateway API GET failed for %s: %s" % (url, err)
            )
        return None

    def paginate(self, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        results: List[Dict] = []
        params = dict(params or {})
        params.setdefault("page_size", 200)
        next_path: Optional[str] = path
        next_params: Dict[str, Any] = params
        while next_path:
            data = self.get(next_path, next_params)
            results.extend(data.get("results") or [])
            nxt = data.get("next")
            if not nxt:
                break
            if nxt.startswith("http://") or nxt.startswith("https://"):
                next_path = nxt.replace(self.base, "", 1)
            else:
                next_path = nxt
            next_params = {}
        return results

    def api(self, suffix: str) -> str:
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        return "%s%s" % (self.api_prefix, suffix)


def verify_gateway_api(module: AnsibleModule, client: ApiClient) -> None:
    """Fail fast if Gateway /api/controller/v2 is unreachable."""
    if client.get(client.api("/me/"), fail_on_error=False) is not None:
        return
    if client.get(client.api("/ping/"), fail_on_error=False) is not None:
        return
    module.fail_json(
        msg=(
            "Unable to reach AAP Gateway Controller API at %s%s. "
            "This demo requires AAP 2.5+ (Platform Gateway). "
            "Check aap_hostname, credentials, and TLS settings."
            % (client.base, GATEWAY_CONTROLLER_API)
        )
    )


def source_host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:  # noqa: BLE001
        return ""


def fqcn_version_from_tarball_url(url: str) -> Optional[Tuple[str, str]]:
    match = RE_TARBALL.search(url)
    if not match:
        return None
    namespace, name, version = match.groups()
    return "%s.%s" % (namespace, name), version


def normalize_git_url(url: str) -> str:
    """Normalize git+https / ssh git URLs to an https URL when possible."""
    text = to_text(url or "").strip()
    if text.startswith("git+"):
        text = text[4:]
    if text.startswith("git@"):
        # git@github.com:org/repo.git → https://github.com/org/repo.git
        rest = text[4:]
        if ":" in rest:
            host, path = rest.split(":", 1)
            text = "https://%s/%s" % (host, path)
    return text.rstrip("/")


def git_short_label(url: str) -> str:
    """Shorten https://github.com/org/repo.git → org/repo."""
    normalized = normalize_git_url(url)
    try:
        path = urlparse(normalized).path.strip("/")
    except Exception:  # noqa: BLE001
        path = normalized
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return "%s/%s" % (parts[-2], parts[-1])
    return parts[-1] if parts else normalized


def repo_basename_from_git_url(url: str) -> str:
    label = git_short_label(url)
    return label.split("/")[-1] if label else ""


def parse_installed_collections(stdout: str) -> Dict[str, Any]:
    """Parse ansible-galaxy collection install stdout into structured data.

    Git installs usually only leave ``Cloning into`` / ``Created collection for``
    lines (no download URL). Label those as ``Git repo`` unless a concrete
    ``.git`` URL also appears in the captured output.
    """
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def upsert(name: str, version: str) -> Dict[str, Any]:
        key = (name, version)
        if key not in by_key:
            by_key[key] = {
                "name": name,
                "version": version,
                "download_url": None,
                "source_host": None,
                "source_server": None,
                "source_type": None,
                "git_url": None,
            }
        return by_key[key]

    def apply_git_url(entry: Dict[str, Any], url: str) -> None:
        entry["source_type"] = "git"
        entry["git_url"] = url
        entry["source_host"] = source_host_from_url(url) or entry.get("source_host")

    for name, version in RE_INSTALLING.findall(stdout):
        upsert(name, version)
    for name, version in RE_INSTALLED_OK.findall(stdout):
        upsert(name, version)

    for name, version, server in RE_OBTAINED.findall(stdout):
        entry = upsert(name, version)
        entry["source_server"] = server
        entry["source_type"] = entry.get("source_type") or "galaxy"

    for url in RE_DOWNLOADING.findall(stdout):
        parsed = fqcn_version_from_tarball_url(url)
        host = source_host_from_url(url)
        if parsed:
            name, version = parsed
            entry = upsert(name, version)
            entry["download_url"] = url
            entry["source_host"] = host or entry.get("source_host")
            entry["source_type"] = "http"

    cloned = set(RE_CLONING.findall(stdout))
    for name, version in RE_CREATED_COLLECTION.findall(stdout):
        if version:
            upsert(name, version)["source_type"] = "git"
        else:
            for (n, _v), entry in by_key.items():
                if n == name:
                    entry["source_type"] = "git"

    for name in cloned:
        for (n, _v), entry in by_key.items():
            if n == name:
                entry["source_type"] = "git"

    # Only link when the git URL itself appears in galaxy stdout/stderr.
    for match in RE_GIT_URL.finditer(stdout):
        url = normalize_git_url(match.group(1) or match.group(2))
        basename = repo_basename_from_git_url(url)
        for (n, _v), entry in by_key.items():
            if n == basename:
                apply_git_url(entry, url)

    for (n, _v), entry in by_key.items():
        if entry.get("source_type") == "git" or n in cloned:
            entry["source_type"] = "git"

    orphan_downloads = []
    matched_urls = {
        c.get("download_url") for c in by_key.values() if c.get("download_url")
    }
    for url in RE_DOWNLOADING.findall(stdout):
        if url not in matched_urls:
            orphan_downloads.append(
                {"download_url": url, "source_host": source_host_from_url(url)}
            )

    collections = sorted(by_key.values(), key=lambda c: (c["name"], c["version"]))
    return {
        "collections": collections,
        "dependency_map_processed": bool(RE_DEP_MAP.search(stdout)),
        "orphan_downloads": orphan_downloads,
        "download_hosts": sorted(
            {
                c["source_host"]
                for c in collections
                if c.get("source_host")
            }
            | {d["source_host"] for d in orphan_downloads if d.get("source_host")}
        ),
    }


def fetch_galaxy_install_output(client: ApiClient, update_id: int) -> str:
    """Galaxy install lines live in runner_on_ok event stdout/stderr, not job stdout."""
    events = client.paginate(client.api("/project_updates/%s/events/" % update_id))
    parts: List[str] = []
    for event in events:
        if event.get("event") != "runner_on_ok":
            continue
        event_data = event.get("event_data") or {}
        task = to_text(event_data.get("task") or "")
        task_l = task.lower()
        res = event_data.get("res") or {}
        stdout = to_text(res.get("stdout") or "")
        stderr = to_text(res.get("stderr") or "")
        blob = "\n".join(x for x in (stdout, stderr) if x.strip())
        if not blob.strip():
            continue
        if "galaxy" not in task_l and "collection" not in task_l and "role" not in task_l:
            if not (
                "Installing '" in blob
                or "Downloading http" in blob
                or "Starting galaxy collection" in blob
                or "Cloning into" in blob
                or "Created collection for" in blob
            ):
                continue
        parts.append(blob)
    return "\n".join(parts)


def list_projects(
    client: ApiClient,
    project_names: List[str],
    organization: Optional[str],
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"order_by": "name"}
    if organization:
        params["organization__name"] = organization
    projects = client.paginate(client.api("/projects/"), params)
    if project_names:
        wanted = {n.strip() for n in project_names if n and str(n).strip()}
        projects = [p for p in projects if p.get("name") in wanted]
        found = {p.get("name") for p in projects}
        missing = sorted(wanted - found)
        if missing:
            # Soft-fail later via empty entries; keep names for the report.
            for name in missing:
                projects.append({"id": None, "name": name, "_missing": True})
    return projects


def latest_updates_for_project(
    client: ApiClient,
    project_id: int,
    since_hours: int,
    updates_per_project: int,
    update_status: str,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "project": project_id,
        "status": update_status,
        "order_by": "-created",
        "page_size": max(updates_per_project, 1),
    }
    if since_hours and since_hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        params["created__gte"] = cutoff.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    updates = client.paginate(client.api("/project_updates/"), params)
    return updates[: max(updates_per_project, 1)]


def _add_source_ref(sources: List[Dict[str, Any]], coll: Dict[str, Any]) -> None:
    """Append a displayable source ref (http host or git repo) once."""
    if coll.get("git_url"):
        ref = {
            "type": "git",
            "label": git_short_label(coll["git_url"]),
            "url": coll["git_url"],
        }
    elif coll.get("source_type") == "git":
        ref = {"type": "git", "label": "Git repo", "url": None}
    elif coll.get("source_host"):
        ref = {
            "type": "host",
            "label": coll["source_host"],
            "url": coll.get("download_url"),
        }
    else:
        return
    for existing in sources:
        if (
            existing.get("type") == ref["type"]
            and existing.get("label") == ref["label"]
            and existing.get("url") == ref["url"]
        ):
            return
    sources.append(ref)


def build_summary(project_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    unique: Dict[str, Dict[str, Any]] = {}
    total_collections = 0
    projects_with_collections = 0
    download_hosts: set = set()

    for project in project_results:
        saw = False
        pname = project.get("project_name")
        pid = project.get("project_id")
        for update in project.get("updates") or []:
            for coll in update.get("collections") or []:
                saw = True
                total_collections += 1
                key = "%s:%s" % (coll.get("name"), coll.get("version"))
                bucket = unique.setdefault(
                    key,
                    {
                        "name": coll.get("name"),
                        "version": coll.get("version"),
                        "projects": [],
                        "source_hosts": [],
                        "source_servers": [],
                        "sources": [],
                    },
                )
                _add_project_ref(bucket["projects"], pid, pname)
                _add_source_ref(bucket["sources"], coll)
                host = coll.get("source_host")
                if host:
                    download_hosts.add(host)
                    if host not in bucket["source_hosts"]:
                        bucket["source_hosts"].append(host)
                server = coll.get("source_server")
                if server and server not in bucket["source_servers"]:
                    bucket["source_servers"].append(server)
            for host in update.get("download_hosts") or []:
                download_hosts.add(host)
        if saw:
            projects_with_collections += 1

    for bucket in unique.values():
        bucket["projects"] = sorted(
            bucket["projects"],
            key=lambda p: (p.get("name") or "").lower(),
        )
        bucket["sources"] = sorted(
            bucket["sources"],
            key=lambda s: (s.get("type") or "", s.get("label") or ""),
        )

    return {
        "projects_inspected": len(project_results),
        "projects_with_collections": projects_with_collections,
        "total_collection_installs": total_collections,
        "unique_collections": len(unique),
        "download_hosts": sorted(download_hosts),
        "collections": sorted(unique.values(), key=lambda c: (c["name"], c["version"])),
    }


def _add_project_ref(
    projects: List[Dict[str, Any]], project_id: Any, project_name: Any
) -> None:
    """Append {id, name} once per project id (or name when id is missing)."""
    if not project_name and project_id is None:
        return
    for existing in projects:
        if project_id is not None and existing.get("id") == project_id:
            return
        if project_id is None and existing.get("name") == project_name:
            return
    projects.append({"id": project_id, "name": project_name})


def run_module() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            aap_hostname=dict(type="str", required=False),
            aap_token=dict(type="str", required=False, no_log=True),
            aap_username=dict(type="str", required=False),
            aap_password=dict(type="str", required=False, no_log=True),
            aap_validate_certs=dict(type="bool", required=False),
            project_names=dict(type="list", elements="str", default=[]),
            organization=dict(type="str", required=False),
            since_hours=dict(type="int", default=168),
            updates_per_project=dict(type="int", default=1),
            update_status=dict(type="str", default="successful"),
            include_raw_stdout=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
        required_one_of=[],
    )

    host = module.params.get("aap_hostname") or _env_first(
        "AAP_HOSTNAME", "CONTROLLER_HOST", "TOWER_HOST"
    )
    token = module.params.get("aap_token") or _env_first(
        "AAP_TOKEN", "CONTROLLER_OAUTH_TOKEN", "TOWER_OAUTH_TOKEN"
    )
    username = module.params.get("aap_username") or _env_first(
        "AAP_USERNAME", "CONTROLLER_USERNAME", "TOWER_USERNAME"
    )
    password = module.params.get("aap_password") or _env_first(
        "AAP_PASSWORD", "CONTROLLER_PASSWORD", "TOWER_PASSWORD"
    )
    validate_certs = module.params.get("aap_validate_certs")
    if validate_certs is None:
        validate_certs = _env_bool(
            True, "AAP_VALIDATE_CERTS", "CONTROLLER_VERIFY_SSL", "TOWER_VERIFY_SSL"
        )
    else:
        validate_certs = _parse_bool(validate_certs, True)
    # fetch_url reads validate_certs from module.params
    module.params["validate_certs"] = validate_certs

    if not host:
        module.fail_json(
            msg=(
                "aap_hostname is required (or set AAP_HOSTNAME). "
                "On AAP, attach a Red Hat Ansible Automation Platform credential "
                "(injects CONTROLLER_HOST, which is also accepted)."
            )
        )
    if not token and not (username and password):
        module.fail_json(
            msg=(
                "Provide aap_token (or AAP_TOKEN / CONTROLLER_OAUTH_TOKEN) "
                "or aap_username + aap_password."
            )
        )

    project_names = module.params.get("project_names") or []
    # Survey textareas often arrive as a single newline/comma-delimited string
    # when passed incorrectly; normalize list-of-one-blob cases in the playbook
    # instead — here just strip empties.
    project_names = [to_text(n).strip() for n in project_names if to_text(n).strip()]

    since_hours = int(module.params.get("since_hours") or 0)
    updates_per_project = max(int(module.params.get("updates_per_project") or 1), 1)
    update_status = to_text(module.params.get("update_status") or "successful")
    include_raw = bool(module.params.get("include_raw_stdout"))
    organization = module.params.get("organization") or None

    client = ApiClient(
        module,
        host,
        token=token,
        username=username,
        password=password,
        validate_certs=validate_certs,
        api_prefix=GATEWAY_CONTROLLER_API,
    )

    if module.check_mode:
        module.exit_json(
            changed=False,
            projects=[],
            summary={
                "projects_inspected": 0,
                "projects_with_collections": 0,
                "total_collection_installs": 0,
                "unique_collections": 0,
                "download_hosts": [],
                "collections": [],
            },
            msg="Check mode: skipped AAP Gateway API inspection",
            api_prefix=GATEWAY_CONTROLLER_API,
            aap_hostname=(host or "").rstrip("/"),
        )

    verify_gateway_api(module, client)

    projects = list_projects(client, project_names, organization)
    results: List[Dict[str, Any]] = []

    for project in projects:
        pname = project.get("name")
        pid = project.get("id")
        entry: Dict[str, Any] = {
            "project_id": pid,
            "project_name": pname,
            "updates": [],
            "error": None,
        }
        if project.get("_missing") or not pid:
            entry["error"] = "Project not found"
            results.append(entry)
            continue

        updates = latest_updates_for_project(
            client, pid, since_hours, updates_per_project, update_status
        )
        if not updates:
            entry["error"] = "No matching project updates found"
            results.append(entry)
            continue

        for update in updates:
            update_id = update["id"]
            stdout = fetch_galaxy_install_output(client, update_id)
            parsed = parse_installed_collections(stdout)
            update_entry: Dict[str, Any] = {
                "update_id": update_id,
                "status": update.get("status"),
                "created": update.get("created"),
                "finished": update.get("finished"),
                "scm_revision": (update.get("summary_fields") or {})
                .get("project", {})
                .get("scm_revision")
                or update.get("scm_revision")
                or project.get("scm_revision"),
                "collections": parsed["collections"],
                "dependency_map_processed": parsed["dependency_map_processed"],
                "orphan_downloads": parsed["orphan_downloads"],
                "download_hosts": parsed["download_hosts"],
            }
            if include_raw:
                update_entry["galaxy_stdout"] = stdout
            entry["updates"].append(update_entry)

        results.append(entry)

    summary = build_summary(results)
    module.exit_json(
        changed=False,
        projects=results,
        summary=summary,
        api_prefix=GATEWAY_CONTROLLER_API,
        aap_hostname=host.rstrip("/"),
    )


if __name__ == "__main__":
    run_module()
