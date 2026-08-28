# Deactivate the AAP Controller subscription

Remove the **locally attached** Ansible Automation Platform (AAP) subscription
from Controller without uninstalling the product.

After this, Controller is unlicensed: the UI opens the subscription wizard, and
job launches fail the license check until the customer either **renews and
re-attaches** a subscription or **uninstalls** AAP.

Official KCS:
[How Do I Deactivate The License/Subscription Information From Ansible Tower or Ansible Automation Platform?](https://access.redhat.com/solutions/6098031)

## What this does and does not do

| Does | Does not |
|------|----------|
| `DELETE` the Controller config endpoint, which clears **only** `settings.LICENSE` | Uninstall AAP, Gateway, Hub, EDA, or the OS |
| Return HTTP `204` on success | Delete other Controller settings (auth, orgs, jobs, `TOWER_URL_BASE`, analytics, …) |
| Require a **Controller superuser** | Revoke the entitlement in the Red Hat Customer Portal / account |
| Work on AAP 2.x and Tower ≥ 3.7 | Remotely disable the instance from Red Hat’s side (there is no kill switch) |

The path is named `/config/`. `GET` returns a bundle of site settings including
`license_info`. `DELETE` does **not** wipe that bundle — it only empties the
license.

OS-level `subscription-manager` registration is separate. Repeat this per
Controller cluster if you have more than one.

## Prerequisites

1. **Network access** from the machine running curl/Ansible to the AAP API
   (Gateway HTTPS on 2.5+, or Controller HTTPS on 2.4 / Tower).
2. **Controller superuser** credentials, or an OAuth2 / personal access token
   for a superuser. Org admins cannot DELETE this endpoint.
3. The correct **API path** for the install (see below).
4. For the playbook: **ansible-core** (the `ansible.builtin.uri` module; no
   extra collections). For curl: any host with `curl`.

Run this from a **workstation**, not as a job template on the same AAP you are
deactivating. After the license is gone, that controller will not launch new
jobs.

Self-signed UI certs: pass `-k` to curl, or set `aap_validate_certs: false`.

## API paths

| Install | Config URL |
|---------|------------|
| AAP 2.5+ (Platform Gateway) | `https://<gateway>/api/controller/v2/config/` |
| AAP 2.4, Tower, or Controller reached directly | `https://<controller>/api/v2/config/` |

If you are unsure, `GET` both. The working one returns JSON with `license_info`
and `version`. A 404 means the wrong prefix.

## Option 1 — curl (no Ansible)

Inspect what is attached:

```bash
# AAP 2.5+
curl -sS -k -u admin 'https://aap.example.com/api/controller/v2/config/' \
  | python3 -m json.tool

# AAP 2.4 / direct Controller
curl -sS -k -u admin 'https://controller.example.com/api/v2/config/' \
  | python3 -m json.tool
```

Look at `license_info`: `subscription_name`, `license_type`, `instance_count`,
`date_expired`, `time_remaining`. An empty `license_info` object (or
`valid_key` false) means nothing is attached.

Deactivate (license only). Expect HTTP **204** and an empty body:

```bash
# AAP 2.5+
curl -sS -k -u admin -X DELETE \
  -o /dev/null -w 'HTTP %{http_code}\n' \
  'https://aap.example.com/api/controller/v2/config/'

# AAP 2.4 / direct Controller
curl -sS -k -u admin -X DELETE \
  -o /dev/null -w 'HTTP %{http_code}\n' \
  'https://controller.example.com/api/v2/config/'
```

Token instead of user/password:

```bash
curl -sS -k -H "Authorization: Bearer ${AAP_TOKEN}" -X DELETE \
  -o /dev/null -w 'HTTP %{http_code}\n' \
  'https://aap.example.com/api/controller/v2/config/'
```

Verify — `license_info` should be empty:

```bash
curl -sS -k -u admin 'https://aap.example.com/api/controller/v2/config/' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("license_info"))'
```

## Option 2 — this playbook

Uses only `ansible.builtin.uri`. Default run is **inspect-only**. The DELETE
runs only when `aap_subscription_confirm=true`.

```bash
cd random/deactivate-aap-subscription
cp vars/subscription.example.yml vars/subscription.yml
# edit aap_hostname, credentials, aap_use_gateway
```

Inspect:

```bash
ansible-playbook playbook.yml -i localhost, -c local -e @vars/subscription.yml
```

Deactivate:

```bash
ansible-playbook playbook.yml -i localhost, -c local -e @vars/subscription.yml \
  -e aap_subscription_confirm=true
```

If the UI cert is untrusted:

```bash
ansible-playbook playbook.yml -i localhost, -c local -e @vars/subscription.yml \
  -e aap_validate_certs=false -e aap_subscription_confirm=true
```

Credentials can also come from the environment: `AAP_HOSTNAME`, `AAP_USERNAME`,
`AAP_PASSWORD`, `AAP_TOKEN`, `AAP_VALIDATE_CERTS`. Extra vars win over env.

| Variable | Default | Meaning |
|----------|---------|---------|
| `aap_hostname` | (required) | Host or `https://host` |
| `aap_use_gateway` | `true` | `true` → `/api/controller/v2/config/` (2.5+); `false` → `/api/v2/config/` |
| `aap_username` / `aap_password` | | Superuser basic auth |
| `aap_token` | | Superuser token; used instead of user/password when set |
| `aap_validate_certs` | `true` | TLS verify |
| `aap_subscription_confirm` | `false` | Must be `true` to DELETE |

`vars/subscription.yml` is gitignored. Keep real passwords out of git.

`--check` prints the current subscription and skips DELETE.

## Option 3 — `ansible.controller` / `awx.awx` collection

If the Controller collection is already installed (typical on AAP execution
environments):

```yaml
- name: Remove license
  ansible.controller.license:
    state: absent
    controller_host: https://aap.example.com
    controller_username: admin
    controller_password: "{{ vault_aap_password }}"
    validate_certs: true
```

That module calls the same `DELETE` on `config`.

## After deactivation

1. Log in to the UI. Superusers are sent to the **subscription wizard**.
2. New job launches are blocked until a valid subscription is attached.
3. Existing resources (inventories, templates, credentials) remain. This is
   not an uninstall.
4. To resume: renew the Red Hat subscription, then attach it in the wizard
   (or `POST` a manifest / subscription id to the same `/config/` URL).
5. To stop using the product: uninstall AAP with the installer / operator
   after the license is cleared (or instead of clearing it).

A subscription that was already attached keeps working until its **end date**,
plus about a **30-day grace period**, unless you DELETE it as above. Not
renewing in the Customer Portal does not by itself wipe the local license.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| HTTP 401 | Bad user/password or token |
| HTTP 403 | Authenticated, but not a Controller **superuser** |
| HTTP 404 | Wrong path (`aap_use_gateway` / 2.4 vs 2.5) |
| TLS error | Self-signed cert — `aap_validate_certs: false` or curl `-k` |
| Playbook ends after the summary with no DELETE | Inspect mode, or nothing was attached (`valid_key` false) |
| UI still shows a subscription | Wrong cluster, or cache; GET `/config/` again and check `license_info` |

## References

- KCS [6098031](https://access.redhat.com/solutions/6098031)
- Controller collection: `ansible.controller.license` / `awx.awx.license` `state: absent`
- Attach a subscription: [Attaching your Ansible Automation Platform subscription to your instance](https://access.redhat.com/articles/5807761)
