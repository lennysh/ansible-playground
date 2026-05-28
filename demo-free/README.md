# demo-free — `strategy: free`

Demonstrates how Ansible's **`free` execution strategy** behaves compared to the default **`linear`** strategy.

## What this shows

With the default `linear` strategy, Ansible runs each task across **all** hosts before moving to the next task — every host waits at a barrier until the slowest host finishes the current task.

With `strategy: free`, each host runs **independently**. A host that finishes a task immediately proceeds to the next one without waiting for the rest of the group. In the output you will see debug messages from different hosts interleaved and out of order, reflecting their individual progress through the task list.

## How it works

The playbook has two plays:

1. **Step 1** — Dynamically creates 10 fake local hosts (`fake-host-1` through `fake-host-10`) using `add_host` and adds them to the `demo_hosts` group. No real remote targets are needed.

2. **Step 2** — Targets `demo_hosts` with `strategy: free`. Each host runs 10 pairs of tasks:
   - A `sleep` with a random duration (0.1–0.9 seconds) to simulate variable host speed
   - A `debug` message confirming that host completed that task number

Because sleep durations differ per host and per task, the interleaved debug output makes the independent execution visually obvious.

## How to run

```bash
ansible-playbook playbook.yml
```

Compare against default behavior by temporarily removing (or commenting out) `strategy: free` and re-running — output will be grouped task-by-task instead of host-by-host.

## Sample output

<!-- Paste raw `ansible-playbook playbook.yml` output below -->

```text

```
