# demo-when — `when:` condition examples and pitfalls

A collection of **`when:` patterns** — from straightforward version checks to subtle bugs that cause tasks to silently skip.

Each task name includes the expected outcome (`RUN` or `SKIP`) so you can compare against actual playbook output.

## Playbook variables

```yaml
ansible_distribution_version: 10.0.20348   # meets the version threshold
enforce_msdtc: false                       # boolean false
optional_flag: "false"                     # string "false" — not the same thing
```

## Examples at a glance

| # | Task | Expect | Why |
|---|------|--------|-----|
| 1 | Version check | RUN | `10.0.20348 >= 10.0.20348` is true |
| 2 | Version OR enforce flag (correct) | RUN | Version clause is true; flag state irrelevant |
| 3 | Inconsistent `default()` on same var | SKIP | Both clauses evaluate false when `enforce_msdtc: false` |
| 4 | Bare string variable | RUN | Jinja2 treats any non-empty string as truthy — including `"false"` |
| 5 | String with `\| bool` filter | SKIP | Ansible's `bool` filter correctly coerces `"false"` to false |
| 6 | `is defined` test | RUN | `enforce_msdtc` is set (even though its value is false) |
| 7 | Missing var with `default(false)` | SKIP | Undefined variable safely falls back to false |
| 8 | AND — both clauses required | SKIP | `enforce_msdtc` is false, so AND short-circuits |
| 9 | OR — either clause sufficient | RUN | Version clause is true regardless of flag state |

## Example details

### Example 1 — Simple version comparison

The most basic pattern: run when the host meets a minimum OS version.

```yaml
when: ansible_distribution_version is version('10.0.20348', '>=')
```

### Example 2 — Correct OR logic

Run when **either** the version threshold is met **or** a feature flag is enabled. Uses a consistent `default(false)` throughout.

```yaml
when: >
  (ansible_distribution_version is version('10.0.20348', '>=')) or
  (enforce_msdtc | default(false) | bool)
```

### Example 3 — Inconsistent `default()` (bug)

Looks like Example 2's inverse, but the inconsistent defaults break the logic:

```yaml
when: |
  (enforce_msdtc | default(false) | bool) or
  (
    (enforce_msdtc | default(true) | bool) and
    (ansible_distribution_version is version('10.0.20348', '>='))
  )
```

- First clause: missing `enforce_msdtc` → `false`
- Second clause: missing `enforce_msdtc` → `true`

With `enforce_msdtc: false` explicitly set, **both** clauses are false and the version check never runs — even though the version threshold is met.

### Examples 4 & 5 — String `"false"` vs boolean `false`

Survey fields and extra vars arrive as **strings**. In Jinja2, `"false"` is a non-empty string and therefore **truthy**:

```yaml
when: optional_flag          # RUN — trap!
when: optional_flag | bool   # SKIP — correct
```

Always pipe user-supplied values through `| bool` when you mean a boolean.

### Examples 6 & 7 — Defined vs missing variables

`is defined` checks whether a variable **exists**, not whether it is truthy. A variable set to `false` is still defined.

For variables that may not exist, use `default()` to avoid undefined-variable errors:

```yaml
when: unset_var | default(false) | bool
```

### Examples 8 & 9 — AND vs OR grouping

Parentheses and operator choice matter. With `enforce_msdtc: false` and a qualifying version:

```yaml
# SKIP — both must be true
when: >
  (enforce_msdtc | bool) and
  (ansible_distribution_version is version('10.0.20348', '>='))

# RUN — either is sufficient
when: >
  (enforce_msdtc | bool) or
  (ansible_distribution_version is version('10.0.20348', '>='))
```

## Things to try

- Set `enforce_msdtc: true` — Examples 2, 3, 8, and 9 all RUN; Example 3 now works via its first clause.
- Remove `enforce_msdtc` entirely — Example 3 RUNs (second clause defaults to `true`), which is probably not what you want.
- Change `optional_flag` to `true` (unquoted) — Example 4 still RUNs; compare behavior with Example 5.
- Change `ansible_distribution_version` to `9.0.0` — Examples 1, 2, and 9 SKIP; only flag-dependent examples can RUN.

## How to run

```bash
ansible-playbook playbook.yml
```

Expected PLAY RECAP: `ok=5`, `skipped=4`.

## Sample output

<!-- Paste raw `ansible-playbook playbook.yml` output below -->

```text
PLAY [WHEN Statement Testing] *****************************************************************************************************************************************************************************************

TASK [Example 1 — version check (expect: RUN)] ************************************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
    "msg": "Version 10.0.20348 meets threshold"
}

TASK [Example 2 — version OR enforce flag, consistent defaults (expect: RUN)] *****************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
    "msg": "Version threshold met OR enforce_msdtc enabled"
}

TASK [Example 3 — inconsistent defaults on enforce_msdtc (expect: SKIP)] **********************************************************************************************************************************************
skipping: [lshirley-thinkpadp1gen7.rmtusga.csb]

TASK [Example 4 — bare string variable (expect: RUN — trap!)] *********************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
    "msg": "optional_flag is the string \"false\", which Jinja2 treats as truthy because it is a non-empty string"
}

TASK [Example 5 — string coerced with bool filter (expect: SKIP)] *****************************************************************************************************************************************************
skipping: [lshirley-thinkpadp1gen7.rmtusga.csb]

TASK [Example 6 — variable is defined (expect: RUN)] ******************************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
    "msg": "enforce_msdtc is defined (value: False)"
}

TASK [Example 7 — missing variable with default fallback (expect: SKIP)] **********************************************************************************************************************************************
skipping: [lshirley-thinkpadp1gen7.rmtusga.csb]

TASK [Example 8 — AND requires both clauses true (expect: SKIP)] ******************************************************************************************************************************************************
skipping: [lshirley-thinkpadp1gen7.rmtusga.csb]

TASK [Example 9 — AND with OR grouped correctly (expect: RUN)] ********************************************************************************************************************************************************
ok: [lshirley-thinkpadp1gen7.rmtusga.csb] => {
    "msg": "Version threshold met; enforce_msdtc state does not matter here"
}

PLAY RECAP ************************************************************************************************************************************************************************************************************
lshirley-thinkpadp1gen7.rmtusga.csb : ok=5    changed=0    unreachable=0    failed=0    skipped=4    rescued=0    ignored=0
```
