# demo-hosts-advanced — Normalizing messy host limit input

Demonstrates how to accept **messy, user-supplied host lists** (such as Ansible Automation Platform survey responses) and normalize them into a clean comma-separated string suitable for a dynamic `hosts:` play target.

## What this shows

In AAP, a survey field might return hostnames in unpredictable formats: comma-separated, one-per-line, mixed case, domain suffixes, extra whitespace, duplicate commas, blank lines, tabs, and leading/trailing separators. This playbook shows a Jinja2 filter pipeline that tolerates all of that and still targets the correct inventory hosts.

The normalization applied:

```jinja2
input | default('')
| regex_replace('[ \t,\r\n]+', ',')   # collapse whitespace/separators to commas
| regex_replace(',+', ',')            # collapse duplicate commas
| regex_replace('.domain.com', '')    # strip domain suffix
| regex_replace('^,|,$', '')           # trim leading/trailing commas
| lower                               # lowercase for inventory matching
```

## CLI demo vs. AAP usage

This playbook is structured so it runs standalone from the command line, but **only Play 3 is what you would carry into AAP**. Plays 1 and 2 exist purely to simulate conditions that AAP already provides.

| Play | CLI demo purpose | In AAP |
|------|------------------|--------|
| **Play 1** | Dynamically registers fake hosts with `add_host` | **Not needed** — hosts come from the job template's attached inventory |
| **Play 2** | Simulates survey input via `set_fact` and previews filter scenarios | **Not needed** — a Survey question on the job template provides the variable directly |
| **Play 3** | Normalizes input and targets `hosts:` dynamically | **This is the real pattern** — apply the filter pipeline to the survey variable |

### Adapting Play 3 for AAP

In the CLI demo, Play 2 stores the raw survey value as a fact on `localhost`, so Play 3 reads it back via `hostvars`:

```yaml
hostvars['localhost']['host_limit'] | default('')
```

In AAP, the survey answer is already available as a job extra variable — there is no `set_fact` step and no need to reach into `hostvars`. Replace the `hostvars` lookup with your survey variable name (shown here as `host_limit`, matching the survey question):

```yaml
- name: Advanced Hosts Var Demo
  hosts: "{{ host_limit_normalized }}"
  gather_facts: false
  vars:
    host_limit_normalized: >-
      {{
        host_limit | default('')
        | regex_replace('[ \t,\r\n]+', ',')
        | regex_replace(',+', ',')
        | regex_replace('.domain.com', '')
        | regex_replace('^,|,$', '')
        | lower
      }}
  tasks:
    # ...
```

- `host_limit` — raw, messy value from the survey question (replaces `hostvars['localhost']['host_limit']`)
- `host_limit_normalized` — filtered result used in `hosts:`

The filter pipeline stays the same; only the **source** of the raw input changes.

## How it works

The playbook has three plays:

1. **Play 1** — Dynamically registers 10 fake local hosts (`fake-host-1` … `fake-host-10`) into the `demo_hosts` group. Standalone CLI scaffolding only.

2. **Play 2** — Simulates an AAP survey response:
   - Defines `host_limit_scenarios` — a dictionary of realistic messy inputs with descriptions
   - Previews every scenario, showing raw input vs. normalized output
   - Sets `host_limit` via `set_fact` on `localhost` (mimics what a survey variable would provide)

3. **Play 3** — The pattern that matters: normalizes the raw host list and uses it as the play's `hosts:` target, then prints each matched host's `inventory_hostname`.

## Things to try

Change `host_limit_scenario` in Play 2 to exercise a specific input pattern:

| Scenario key        | What it tests                                      |
|---------------------|----------------------------------------------------|
| `csv`               | Comma-separated list with domains and mixed case   |
| `multiline`         | One hostname per line                              |
| `whitespace`        | Tabs, spaces, and newlines as separators           |
| `duplicate_commas`  | Double/triple commas between entries               |
| `leading_trailing`  | Leading/trailing commas and surrounding whitespace |
| `empty_lines`       | Blank lines in multiline input                     |
| `domains_and_case`  | Domain stripping and lowercasing                   |
| `messy_all`         | All of the above combined (default)                |

## How to run

```bash
ansible-playbook playbook.yml
```

## Sample output

<!-- Paste raw `ansible-playbook playbook.yml` output below -->

```text
PLAY [Play 1 - Register hosts in inventory (not needed in AAP)] *******************************************************************************************************************************************************

TASK [Add fake hosts to inventory] ************************************************************************************************************************************************************************************
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-1)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-2)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-3)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-4)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-5)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-6)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-7)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-8)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-9)
changed: [lennysh-laptop] => (item=Dynamically adding fake-host-10)

PLAY [Play 2 - Set host_limit (simulating an AAP Survey response)] ****************************************************************************************************************************************************

TASK [Preview all host_limit filter scenarios] ************************************************************************************************************************************************************************
ok: [lennysh-laptop] => (item=csv) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7.domain.com,FAKE-HOST-8,Fake-Host-9,fake-host-10",
        "scenario": "csv — Comma-separated list with domain suffix and mixed case"
    }
}
ok: [lennysh-laptop] => (item=multiline) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": "fake-host-1\nfake-host-2\nfake-host-3\nfake-host-4\nfake-host-5\nfake-host-6\nfake-host-7.domain.com\nFAKE-HOST-8\nFake-Host-9\nfake-host-10\n",
        "scenario": "multiline — One host per line (multiline survey field)"
    }
}
ok: [lennysh-laptop] => (item=whitespace) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6",
        "raw": "fake-host-1\tfake-host-2 fake-host-3\nfake-host-4 fake-host-5 fake-host-6",
        "scenario": "whitespace — Tabs, spaces, and newlines used as separators"
    }
}
ok: [lennysh-laptop] => (item=duplicate_commas) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5",
        "raw": "fake-host-1,,fake-host-2,,,fake-host-3,,fake-host-4,,,fake-host-5",
        "scenario": "duplicate_commas — Duplicate commas between hostnames"
    }
}
ok: [lennysh-laptop] => (item=leading_trailing) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4",
        "raw": "  , fake-host-1 , fake-host-2 , fake-host-3 , fake-host-4 ,  ",
        "scenario": "leading_trailing — Leading/trailing commas and surrounding whitespace"
    }
}
ok: [lennysh-laptop] => (item=empty_lines) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4",
        "raw": "fake-host-1\n\nfake-host-2\n\n\nfake-host-3\n\nfake-host-4\n",
        "scenario": "empty_lines — Blank lines mixed into multiline input"
    }
}
ok: [lennysh-laptop] => (item=domains_and_case) => {
    "msg": {
        "normalized": "fake-host-7,fake-host-8,fake-host-9",
        "raw": "FAKE-HOST-7.domain.com, FAKE-HOST-8, Fake-Host-9",
        "scenario": "domains_and_case — Domain suffix stripping and lowercasing"
    }
}
ok: [lennysh-laptop] => (item=messy_all) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": ", FAKE-HOST-1.domain.com,,\n\tfake-host-2\tFAKE-HOST-3.domain.com\n\n,,fake-host-4 ,,\n\nfake-host-5,,fake-host-6\n FAKE-HOST-7.domain.com ,, Fake-Host-8\n,fake-host-9,,fake-host-10 ,\n",
        "scenario": "messy_all — Combined messy survey input exercising all filters"
    }
}

TASK [Set host_limit] *************************************************************************************************************************************************************************************************
ok: [lennysh-laptop -> localhost]

TASK [Debug active scenario] ******************************************************************************************************************************************************************************************
ok: [lennysh-laptop] => {
    "msg": {
        "raw": ", FAKE-HOST-1.domain.com,,\n\tfake-host-2\tFAKE-HOST-3.domain.com\n\n,,fake-host-4 ,,\n\nfake-host-5,,fake-host-6\n FAKE-HOST-7.domain.com ,, Fake-Host-8\n,fake-host-9,,fake-host-10 ,\n",
        "scenario": "messy_all — Combined messy survey input exercising all filters"
    }
}

PLAY [Advanced Hosts Var Demo] ****************************************************************************************************************************************************************************************

TASK [Debug host_limit] ***********************************************************************************************************************************************************************************************
ok: [fake-host-1] => {
    "msg": "Hosts: fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10"
}

TASK [Debug Host] *****************************************************************************************************************************************************************************************************
ok: [fake-host-1] => {
    "msg": "Hosts: fake-host-1"
}
ok: [fake-host-2] => {
    "msg": "Hosts: fake-host-2"
}
ok: [fake-host-4] => {
    "msg": "Hosts: fake-host-4"
}
ok: [fake-host-3] => {
    "msg": "Hosts: fake-host-3"
}
ok: [fake-host-5] => {
    "msg": "Hosts: fake-host-5"
}
ok: [fake-host-6] => {
    "msg": "Hosts: fake-host-6"
}
ok: [fake-host-8] => {
    "msg": "Hosts: fake-host-8"
}
ok: [fake-host-7] => {
    "msg": "Hosts: fake-host-7"
}
ok: [fake-host-9] => {
    "msg": "Hosts: fake-host-9"
}
ok: [fake-host-10] => {
    "msg": "Hosts: fake-host-10"
}

PLAY RECAP ************************************************************************************************************************************************************************************************************
fake-host-1                : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-10               : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-2                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-3                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-4                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-5                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-6                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-7                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-8                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
fake-host-9                : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
lennysh-laptop : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```
