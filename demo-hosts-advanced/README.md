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

```
