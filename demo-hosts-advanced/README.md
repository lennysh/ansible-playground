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

## How it works

The playbook has three plays:

1. **Play 1** — Dynamically registers 10 fake local hosts (`fake-host-1` … `fake-host-10`) into the `demo_hosts` group. This step is only needed for standalone CLI runs; in AAP the hosts already exist in inventory.

2. **Play 2** — Simulates an AAP survey response:
   - Defines `host_limit_scenarios` — a dictionary of realistic messy inputs with descriptions
   - Previews every scenario, showing raw input vs. normalized output
   - Sets `host_limit` from the active scenario (controlled by `host_limit_scenario`, default `messy_all`)

3. **Play 3** — Uses the normalized `host_limit` as the play's `hosts:` target and prints each matched host's `inventory_hostname`.

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
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-1)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-2)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-3)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-4)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-5)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-6)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-7)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-8)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-9)
changed: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=Dynamically adding fake-host-10)

PLAY [Play 2 - Set host_limit (simulating an AAP Survey response)] ****************************************************************************************************************************************************

TASK [Preview all host_limit filter scenarios] ************************************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=csv) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7.domain.com,FAKE-HOST-8,Fake-Host-9,fake-host-10",
        "scenario": "csv — Comma-separated list with domain suffix and mixed case"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=multiline) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": "fake-host-1\nfake-host-2\nfake-host-3\nfake-host-4\nfake-host-5\nfake-host-6\nfake-host-7.domain.com\nFAKE-HOST-8\nFake-Host-9\nfake-host-10\n",
        "scenario": "multiline — One host per line (multiline survey field)"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=whitespace) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6",
        "raw": "fake-host-1\tfake-host-2 fake-host-3\nfake-host-4 fake-host-5 fake-host-6",
        "scenario": "whitespace — Tabs, spaces, and newlines used as separators"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=duplicate_commas) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5",
        "raw": "fake-host-1,,fake-host-2,,,fake-host-3,,fake-host-4,,,fake-host-5",
        "scenario": "duplicate_commas — Duplicate commas between hostnames"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=leading_trailing) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4",
        "raw": "  , fake-host-1 , fake-host-2 , fake-host-3 , fake-host-4 ,  ",
        "scenario": "leading_trailing — Leading/trailing commas and surrounding whitespace"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=empty_lines) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4",
        "raw": "fake-host-1\n\nfake-host-2\n\n\nfake-host-3\n\nfake-host-4\n",
        "scenario": "empty_lines — Blank lines mixed into multiline input"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=domains_and_case) => {
    "msg": {
        "normalized": "fake-host-7,fake-host-8,fake-host-9",
        "raw": "FAKE-HOST-7.domain.com, FAKE-HOST-8, Fake-Host-9",
        "scenario": "domains_and_case — Domain suffix stripping and lowercasing"
    }
}
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => (item=messy_all) => {
    "msg": {
        "normalized": "fake-host-1,fake-host-2,fake-host-3,fake-host-4,fake-host-5,fake-host-6,fake-host-7,fake-host-8,fake-host-9,fake-host-10",
        "raw": ", FAKE-HOST-1.domain.com,,\n\tfake-host-2\tFAKE-HOST-3.domain.com\n\n,,fake-host-4 ,,\n\nfake-host-5,,fake-host-6\n FAKE-HOST-7.domain.com ,, Fake-Host-8\n,fake-host-9,,fake-host-10 ,\n",
        "scenario": "messy_all — Combined messy survey input exercising all filters"
    }
}

TASK [Set host_limit] *************************************************************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb -> localhost]

TASK [Debug active scenario] ******************************************************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
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
lshirley-thinkpadp1gen7.rmtusga.csb : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0 
```
