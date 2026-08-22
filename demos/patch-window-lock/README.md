# demos/patch-window-lock — Cross-team patch lease in `facts.d` (AAP-only)

ORGA handles **host** patching. ORGB handles **app** patching. If both run at
once (especially across a reboot), they step on each other. Both teams call the
**same role** and follow the **same AAP steps**; only `patch_lock_owner` differs.

The role writes a **lease** (not a boolean) to `/etc/ansible/facts.d/patch_lock.fact`.
The next job gathers `ansible_local.patch_lock` and either fails, skips the busy
hosts, or waits until the lease is released / expires.

This demo is **AAP-only**. The lease keys off controller-injected
`tower_workflow_job_id` / `awx_workflow_job_id` (Work and the always-node
Release job share it, so Release does not treat this run as a foreign lock)
and `tower_job_id` / `awx_job_id` when a job template is launched directly.
There is no stable equivalent on a laptop `ansible-playbook` process.

Rescue is the wrong cleanup tool: it runs on **failure**, not success, so a
completed patch would never clear the lock. This demo uses `block/always` plus
an AAP workflow **always-node** Release job.

## Who is who

| Team | What they patch | Workflow | `patch_lock_owner` | Default TTL |
|------|-----------------|----------|--------------------|-------------|
| ORGA | Host / OS | **Demo \| Patch Window \| Host Patch** | `host-patch` | 60 minutes |
| ORGB | Application | **Demo \| Patch Window \| App Patch** | `app-patch` | 20 minutes |

Playground stays **one** AAP organization. The two workflows simulate the two
teams. Launch **both workflows at once** (two browser tabs) — not one workflow
that runs both orgs.

TTL is per launch (survey) so a long host-patch window and a short app-patch
window expire independently. Set `patch_lock_ttl_minutes` (or
`patch_lock_ttl_seconds` to override). Abandoned leases (cancelled job, crashed
EE, host never came back) can be stolen after TTL without Force.

## Lock identity

| Source | When | What it identifies |
|--------|------|--------------------|
| `awx_workflow_job_id` / `tower_workflow_job_id` | Job ran from a workflow | **This patch run.** Work writes it as `lock_id`; the always-node Release job has the same value, so it clears our lease and leaves the other team's. |
| `awx_job_id` / `tower_job_id` | Job template launched directly | Fallback. In-play `always` is the same job, so it still matches. A standalone Release JT is a *different* job id — use Force or owner-only. |
| Optional extra-var `patch_lock_id` | Lab / tests | Overrides the lookup order (after an in-play persisted id). |

Same owner + same `lock_id` = our lease (idempotent re-acquire, not a conflict).
Same owner, different `lock_id` = another job from that team (conflict).

## How the lease works

File: `/etc/ansible/facts.d/patch_lock.fact` → `ansible_local.patch_lock`

```json
{
  "locked": true,
  "owner": "host-patch",
  "lock_id": "55",
  "job_id": "1234",
  "workflow_job_id": "55",
  "started_at": "2026-08-22T13:31:00Z",
  "started_epoch": 1755869460,
  "ttl_seconds": 3600,
  "ttl_minutes": 60
}
```

Acquire is **two-phase** and needs `strategy: linear` (the play default):

1. `setup` on **every** host. No writes yet.
2. Foreign unexpired lock = conflict. Expired or `patch_lock_force` = steal.
   Same owner + same lock id = idempotent re-acquire.
3. `patch_lock_fail_on_conflict=true` (default): **fail every host** with the
   busy list (includes `job_id` / TTL remaining). No writes.
4. `false`: print a comma-separated `--limit` string, `set_stats` it, then
   `meta: end_host` on busy hosts. If **all** hosts would be skipped, the job
   **fails** (still includes the `--limit` string) so AAP is not green.
5. Write JSON, `setup` again. If `owner` / `lock_id` is not us, we lost the
   race — treat as conflict and **do not** delete the winner.

Release deletes the file only if we own it (`lock_id` matches), it is expired,
or Force is set. Never deletes another owner's live lease. Idempotent if
already gone.

`strategy: free` would let some hosts write before others finish the check.
Keep these plays linear.

## Cleanup: `always` plus workflow always-node

```text
Work play:
  block:
    - acquire
    - pause (demo hold)
    - pretend to patch
  always:
    - release   # same job_id; success, task failure, most unreachable-after-work

AAP workflow (Host Patch and App Patch, identical graph):
  Work --always--> Release   # same workflow_job_id as Work
```

| Path | What it covers |
|------|----------------|
| In-play `always` | Normal success and task failure. Matches `lock_id` (same job, and same workflow id when launched from a WJT). |
| Workflow always-node | AAP **job cancel** / SIGTERM, where Ansible often never reaches `always`. Matches `lock_id` = workflow job id. |
| TTL | Controller/EE death or host stays down — no Ansible cleanup at all. Next acquire steals after `ttl_minutes`. |
| Force / standalone Release | Steal now, or clear that owner's lease when there is no workflow id (stuck-lock JT). |

Prefer launching the **workflow** templates. Direct Work JT launch still has
in-play `always`, but AAP **cancel** often never reaches that block; the
workflow always-node still runs.

## How to run (AAP)

1. Re-run **Playground \| Apply CaC** and select **Patch Window Lock**.
2. Open two tabs: **Demo \| Patch Window \| Host Patch** and
   **Demo \| Patch Window \| App Patch**.
3. Launch Host Patch first (inventory = your Linux hosts, Fail = true,
   Hold = 90, TTL = 60). Privilege escalation must be enabled (it is on the JT).
4. While Work is paused, launch App Patch on the **same inventory** (Fail =
   true, TTL = 20). It should fail with the host-patch lease listed (`job_id`,
   TTL remaining).
5. Re-launch App Patch with Fail = **false**. If every targeted host is still
   busy, the job fails and the message contains `--limit host1,host2`. If only
   some are busy, those are skipped and the rest proceed. Paste the CSV into
   **Limit** on a later launch.
6. Cancel a Work node mid-pause: the workflow should still run **Release** and
   clear *this* workflow's lease (the other team's lock is left alone).
7. To demo TTL steal, set Host Patch TTL to 1 minute, kill the controller-side
   job hard enough that Release cannot run, wait, then launch App Patch.

| Object | CaC name |
|--------|----------|
| Workflow (ORGA) | `Demo \| Patch Window \| Host Patch` |
| Workflow (ORGB) | `Demo \| Patch Window \| App Patch` |
| Shared work JT | `Demo \| Patch Window \| Work` |
| Shared release JT | `Demo \| Patch Window \| Release` |

`playbook.yml` in this directory only fails with a pointer here. Lab without a
controller: `ansible-playbook playbook-aap.yml -i INVENTORY --become -e tower_workflow_job_id=1 -e tower_job_id=2`.

## Role extra vars

| Variable | Default | Meaning |
|----------|---------|---------|
| `patch_lock_state` | `acquire` | `acquire` or `release` |
| `patch_lock_owner` | `cli` | Team identity written into the lease |
| `patch_lock_fail_on_conflict` | `true` | Fail-all vs skip busy hosts |
| `patch_lock_force` | `false` | Steal a live foreign lease |
| `patch_lock_ttl_minutes` | `240` (role) / `60` or `20` (WJTs) | Lease lifetime |
| `patch_lock_ttl_seconds` | unset | When set, wins over minutes |
| `patch_lock_hold_seconds` | playbook `90` | Demo pause only — omit in production |
| `patch_lock_fact_dir` | `/etc/ansible/facts.d` | Needs become |
| `patch_lock_release_match_owner_only` | `false` (`true` on Release JT) | Owner-only match when **not** in a workflow (standalone stuck-lock). Ignored when `tower_workflow_job_id` is set. |

Survey booleans arrive as strings; the role pipes them through `| bool`.

## Production notes

- Publish `patch_window_lock` in a collection; this demo keeps it in-tree.
- Drop the `pause` / `patch_lock_hold_seconds` tasks. Keep acquire at the start
  of the work play and `always: release` at the end. Wrap with a workflow
  always-node Release job for cancel.
- Pick TTL from the real patch window (host team vs app team), not a shared
  global. Too short: a still-running job can have its lease stolen. Too long:
  a crashed job blocks the other team until Force or TTL.
- `become` is required for `/etc/ansible/facts.d`. The lock **survives reboot**
  (it is a file); the same play's `always` still runs after the `reboot`
  module comes back.

## Things to try

- `cat /etc/ansible/facts.d/patch_lock.fact` during the pause — JSON lease with
  `workflow_job_id`, then gone after `always` or the Release node.
- Two Host Patch launches on the same hosts: the second conflicts (same owner,
  different workflow job id).
- `patch_lock_ttl_minutes=1` then wait; the next owner should steal with a
  "Stealing patch lock" note.
- Fail = false while the other owner holds every host in the limit — job fails
  and the message includes `--limit host1,host2`.
