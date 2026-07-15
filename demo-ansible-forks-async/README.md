# demo-ansible-forks-async — Forks and async jobs

Demonstrates how Ansible **`forks`** limit parallel host work, and how **`async` + `poll: 0`** lets long-running remote jobs continue **without holding a controller fork**.

The playbook sets **`forks = 3`** in [`ansible.cfg`](ansible.cfg) while targeting **8 hosts**, so blocking (synchronous) work visibly saturates the fork pool. A background monitor plus inline snapshots show worker fork counts **before**, **during**, and **after** async jobs are launched.

## What this shows

| Concept | Behavior in this demo |
|---------|------------------------|
| **`forks`** | At most 3 worker processes run host tasks at once (see `ansible.cfg`). |
| **Blocking `sleep`** | Each active host ties up a fork until the sleep finishes. With 8 hosts, work runs in ~3-host waves. |
| **`async` + `poll: 0`** | Ansible starts the remote sleep and returns immediately. Remote processes keep running, but controller forks are freed. |
| **Follow-up sync work while async runs** | After async jobs are fired, another blocking sleep still runs — proving forks are available again. |

## CLI demo vs. AAP usage

| Step | CLI demo purpose | In AAP |
|------|------------------|--------|
| **Step 0–1** | Start fork monitor + create 8 fake local hosts | **Step 0 only** — monitor still runs on controller via `delegate_to: localhost`; hosts come from inventory |
| **Step 2** | Sync vs async fork comparison | **This is the real pattern** — use [`playbook-aap.yml`](playbook-aap.yml) |
| **Step 3** | Summarize monitor samples into `fork-report.txt` | Same report tasks are at the bottom of `playbook-aap.yml` |

Copy [`ansible.cfg`](ansible.cfg) into the project or set **Forks** on the job template to `3` so the comparison stays visible.

## How it works

1. **Background monitor** — [`files/fork_monitor.py`](files/fork_monitor.py) samples ansible-playbook worker processes every 0.5s and writes [`fork-samples.json`](fork-samples.json). Phase markers in [`fork-demo-phase.txt`](fork-demo-phase.txt) label each sample.

2. **Inline snapshots** — [`files/count_forks.py`](files/count_forks.py) is invoked at explicit checkpoints and records `worker_forks` plus `blocking_slots` into [`fork-snapshots.json`](fork-snapshots.json).

3. **Blocking slot files** — synchronous sleeps touch a per-host file under `active-blocking-slots/` for the duration of the sleep, giving a second observable gauge of concurrent blocking work.

4. **Work phases**
   - **sync_blocking** — all hosts run a 12s synchronous sleep (forks stay busy).
   - **async_fire / async_running** — all hosts launch a 20s sleep with `poll: 0`; snapshot immediately after shows lower fork usage while remote sleeps continue.
   - **async_with_followup_sync** — another 6s blocking sleep while async jobs are still running.

5. **Report** — [`files/summarize_forks.py`](files/summarize_forks.py) prints peak fork counts per phase plus inline snapshots.

## How to run

```bash
cd demo-ansible-forks-async
ansible-playbook playbook.yml
```

Optional tuning via extra vars:

```bash
ansible-playbook playbook.yml \
  -e demo_host_count=8 \
  -e demo_sync_sleep_seconds=12 \
  -e demo_async_sleep_seconds=20
```

After the run, inspect the report:

```bash
cat fork-report.txt
```

## What to look for

- **`sync_blocking` peak** in the report should reach **`3`** for both `worker_forks` and `blocking_slots` while only three hosts run the long sleep at a time.
- **`while_async_jobs_running` snapshot** should show **lower `worker_forks`** than during sync blocking — typically **`0`–`1`** right after all async jobs are dispatched — even though 8 remote `sleep` processes are still running.
- **Follow-up sync** completes in ~3-host waves again, demonstrating forks were available for new blocking work while async jobs continued in the background.

## Files

| File | Purpose |
|------|---------|
| [`ansible.cfg`](ansible.cfg) | Sets `forks = 3` for a visible bottleneck |
| [`playbook.yml`](playbook.yml) | Full CLI demo with fake hosts |
| [`playbook-aap.yml`](playbook-aap.yml) | AAP-ready single play |
| [`files/count_forks.py`](files/count_forks.py) | One-shot fork counter (also used by monitor) |
| [`files/fork_monitor.py`](files/fork_monitor.py) | Continuous background sampler |
| [`files/summarize_forks.py`](files/summarize_forks.py) | Builds `fork-report.txt` |

Generated artifacts (`fork-samples.json`, `fork-report.txt`, etc.) are gitignored.

## Sample report

```text
Continuous monitor peaks by phase (worker_forks):
  - sync_blocking: max worker_forks=3, max blocking_slots=3
  - async_running: max worker_forks=1, max blocking_slots=0
  - async_with_followup_sync: max worker_forks=3, max blocking_slots=3

Inline snapshots:
  - while_async_jobs_running: worker_forks=1 blocking_slots=0 (phase=async_running)
```

During **sync_blocking**, both metrics peak at **3** (matching configured forks). After async jobs fire, **worker_forks** drops while remote sleeps continue, then rises again for follow-up sync work.

## Things to try

- Raise `forks` in `ansible.cfg` to `8` and re-run — sync blocking finishes faster and peaks match the new limit.
- Change `poll: 0` to `poll: 10` on the async task and compare how long forks stay busy.
- Increase `demo_host_count` to 20 to make the 3-fork bottleneck more obvious in job duration.
