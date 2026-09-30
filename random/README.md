# Random playbooks

Grab-bag utilities — not teaching demos, and not loaded by
**Playground | Apply CaC**.

Demos that explain a concept stay under [demos/](../demos/README.md).

| Playbook | Purpose |
|----------|---------|
| [run-commands](run-commands/README.md) | Loop `ansible.builtin.command` over a list of module/task params; debug stdout/stderr |
| [deactivate-aap-subscription](deactivate-aap-subscription/README.md) | Remove the locally attached AAP Controller subscription (`DELETE /config/`, license only) |
| [automation-hub-service-account-auth](automation-hub-service-account-auth/README.md) | Proof that a Hybrid Console service account can auth to hosted Automation Hub (short-lived JWT + ansible-galaxy shim) |
