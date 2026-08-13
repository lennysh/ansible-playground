# Workflow Job Template verbosity override

Ansible Automation Platform workflow job templates (WJTs) cannot prompt for
**verbosity** on the child job templates they run. This demo shows a reusable
pattern:

1. **Survey** on the WJT for verbosity (labels match the Job Template verbosity
   dropdown: `0 (Normal)` … `5 (WinRM Debug)`).
2. **Manage Verbosity** job — one job template used twice in the workflow: the
   first node passes `wjt_verbosity_mode: set`, the last passes `reset`. Each
   call updates the controller `verbosity` field on a configured list of job
   templates via the API (skipped when the survey value is the default).
3. **Sample steps** — child job templates that run at the updated verbosity.

The Manage Verbosity job template is **workflow-agnostic**: point it at any list
of job template names through `extra_vars`, and pass `wjt_verbosity_mode` per
workflow node via `extra_data`.

## Architecture

Survey `wjt_verbosity_level` is on the **workflow** launch form (not a node in
the visualizer). Node **identifiers** match CaC / the Workflow Visualizer. Set
and reset nodes both run the same JT; mode comes from node `extra_data`:

```mermaid
flowchart LR
  start((Start))
  set["wjt-verbosity-set<br/>Manage Verbosity<br/>mode=set"]
  stepA["wjt-verbosity-step-a<br/>Sample Step A"]
  stepB["wjt-verbosity-step-b<br/>Sample Step B"]
  reset["wjt-verbosity-reset<br/>Manage Verbosity<br/>mode=reset"]

  start --> set
  set -->|On success| stepA
  set -->|On fail| reset
  stepA -->|On success| stepB
  stepA -->|On fail| reset
  stepB -->|Always| reset

  linkStyle 0 stroke:#2b9af3,stroke-width:2px
  linkStyle 1 stroke:#3e8635,stroke-width:2px
  linkStyle 2 stroke:#f0ab00,stroke-width:2px
  linkStyle 3 stroke:#3e8635,stroke-width:2px
  linkStyle 4 stroke:#f0ab00,stroke-width:2px
  linkStyle 5 stroke:#2b9af3,stroke-width:2px
```

| Visualizer edge | CaC field | Meaning |
|-----------------|-----------|---------|
| Green **On success** | `success_nodes` | Run the next sample step |
| Amber **On fail** | `failure_nodes` | Skip remaining samples; run reset |
| Blue **Always** | `always_nodes` | Run reset whether Step B succeeds or fails |

Set and reset both skip API calls when survey verbosity is the default (`0`).

| Object | CaC name |
|--------|----------|
| Workflow | `Demo \| WJT Verbosity` |
| Manage verbosity (API set + reset) | `Demo \| WJT Verbosity \| Manage Verbosity` |
| Sample child A | `Demo \| WJT Verbosity \| Sample Step A` |
| Sample child B | `Demo \| WJT Verbosity \| Sample Step B` |

## Launch in AAP

1. Re-run **Playground \| Apply CaC** and select the **WJT Verbosity** demo
   (creates three job templates and the workflow).
2. Open **Templates → Workflow Templates → Demo \| WJT Verbosity**.
3. Launch and pick **Verbosity** (0 = Normal … 5 = WinRM Debug).
4. Inspect the set step output, then the sample steps (higher verbosity shows
   more `debug` tasks and module detail), then the reset step.

**Default verbosity (0):** Set and reset both log a skip message and do not call
the API; sample steps run at whatever verbosity is already on their templates.

**Sample step failures:** Reset is wired with `failure_nodes` (from set and
Sample Step A) and `always_nodes` (from Sample Step B), so elevated verbosity
is restored when a middle step fails — but only when the survey level was
non-zero (reset skips API calls at default verbosity, same as set).

**CLI reset** (`wjt_verbosity_mode=reset` without `wjt_verbosity_level`) still
calls the API so you can force-restore templates outside a workflow.

## Configuring targets (reuse pattern)

On the Manage Verbosity job template, `extra_vars` define which templates to
touch:

```yaml
wjt_verbosity_target_job_templates:
  - "Demo | WJT Verbosity | Sample Step A"
  - "Demo | WJT Verbosity | Sample Step B"
wjt_verbosity_default: 0
```

To use this pattern in another WJT:

1. Add **Manage Verbosity** as the first and last workflow nodes.
2. On the set node, set `extra_data: { wjt_verbosity_mode: set }`; on the reset
   node, `extra_data: { wjt_verbosity_mode: reset }`.
3. Keep **Prompt for extra variables** enabled on the JT (`ask_variables_on_launch:
   true` in CaC) so node `extra_data` is accepted.
4. Either keep the default `extra_vars` target list on the JT, or override
   `wjt_verbosity_target_job_templates` on the workflow node for that workflow
   only.
5. Add a WJT survey question `wjt_verbosity_level` (multiple choice, same labels
   as Job Template verbosity) — workflow survey answers propagate to child nodes.

Only list job templates that should run at the elevated verbosity — omit the
Manage Verbosity template itself.

## Survey (workflow)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `wjt_verbosity_level` | multiple choice | `0 (Normal)` | Controller JT verbosity applied to targets before sample steps |

Choices (searchable dropdown in AAP, same as JT verbosity):

| Value |
|-------|
| `0 (Normal)` |
| `1 (Verbose)` |
| `2 (More Verbose)` |
| `3 (Debug)` |
| `4 (Connection Debug)` |
| `5 (WinRM Debug)` |

The playbook parses the leading integer from the survey answer.

## CLI (API helper only)

```bash
cd demos/wjt-verbosity
ansible-galaxy collection install -r collections/requirements.yml
cp vars/wjt_verbosity.example.yml vars/wjt_verbosity.yml
# edit targets / level / mode

export AAP_HOSTNAME=https://aap.example.com
export AAP_TOKEN=...

ansible-playbook playbook.yml -e @vars/wjt_verbosity.yml
```

## Files

| File | Purpose |
|------|---------|
| `playbook-aap-verbosity.yml` | WJT set/reset nodes — mode from `wjt_verbosity_mode` |
| `playbook-aap-sample-step.yml` | Shared sample child playbook |
| `roles/wjt_verbosity_api/` | API logic (`ansible.controller.job_template`) |
| `playbook.yml` | CLI wrapper for set/reset testing |

## Notes

- Updates the **job template** `verbosity` field, not per-workflow-node prompts
  (WJTs do not expose node-level verbosity for arbitrary child JTs).
- Requires **AAP Credential** on the Manage Verbosity job template.
- Concurrent workflow runs that target the same job templates can race; scope
  targets per workflow or serialize runs if that matters in production.
