# demo-ansible-filters — ansible.builtin filter reference

Runnable examples of every **`ansible.builtin` filter** shipped with ansible-core (70 filters). Each task prints one filter expression and its result.

For stock **Jinja2** filters (`abs`, `map`, `join`, etc.) see [demo-jinja2-filters](../demo-jinja2-filters/README.md).

## What this shows

| Concept | Where it lives |
|---------|----------------|
| Sample data | Play `vars` in [`playbook.yml`](playbook.yml) |
| `fileglob` targets | [`files/sample-a.txt`](files/sample-a.txt), [`files/sample-b.log`](files/sample-b.log) |
| `mandatory` failure | Isolated second play (task uses `ignore_errors: true`) |
| `vault` / `unvault` pair | Encrypt with `set_fact`, decrypt in the next task |
| AAP entry point | [`playbook-aap.yml`](playbook-aap.yml) imports the CLI playbook |

All filters execute on the **controller** during templating. `fileglob`, `realpath`, and `expanduser` inspect the machine running `ansible-playbook`.

## Filter index

| Filter | Example | Notes |
|--------|---------|-------|
| `b64encode` | `{{ 'ansible' \| b64encode }}` | Base64 encode |
| `b64decode` | `{{ 'YW5zaWJsZQ==' \| b64decode }}` | Base64 decode |
| `basename` | `{{ '/etc/hosts' \| basename }}` | POSIX path base name |
| `bool` | `{{ 'false' \| bool }}` | Coerce survey strings to boolean |
| `checksum` | `{{ 'ansible' \| checksum }}` | Data checksum |
| `combinations` | `{{ list \| combinations(2) \| list }}` | n-combinations |
| `combine` | `{{ a \| combine(b, recursive=True) }}` | Merge dicts |
| `comment` | `{{ text \| comment(decoration=' # ') }}` | Comment out lines |
| `commonpath` | `{{ paths \| commonpath }}` | Shared path prefix |
| `dict2items` | `{{ dict \| dict2items }}` | Dict → `[{key, value}, …]` |
| `difference` | `{{ a \| difference(b) }}` | Set difference on lists |
| `dirname` | `{{ '/etc/hosts' \| dirname }}` | POSIX directory |
| `expanduser` | `{{ '~' \| expanduser }}` | Expand `~` |
| `expandvars` | `{{ '$VAR' \| expandvars }}` | Expand `$VAR` from environment |
| `extract` | `{{ 1 \| extract(['a','b','c']) }}` | Index/key lookup |
| `fileglob` | `{{ pattern \| fileglob }}` | Controller glob |
| `flatten` | `{{ nested \| flatten(levels=2) }}` | Flatten nested lists |
| `from_json` | `{{ json_str \| from_json }}` | Parse JSON |
| `from_yaml` | `{{ yaml_str \| from_yaml }}` | Parse YAML |
| `from_yaml_all` | `{{ stream \| from_yaml_all \| list }}` | Multi-doc YAML |
| `hash` | `{{ 'ansible' \| hash('sha256') }}` | Generic hash |
| `human_readable` | `{{ 1536000 \| human_readable }}` | Bytes → human size |
| `human_to_bytes` | `{{ '1.5 MB' \| human_to_bytes }}` | Human size → bytes |
| `intersect` | `{{ a \| intersect(b) }}` | List intersection |
| `items2dict` | `{{ items \| items2dict }}` | `[{key, value}]` → dict |
| `log` | `{{ 1024 \| log(2) }}` | Logarithm |
| `mandatory` | `{{ var \| mandatory }}` | Fail if undefined |
| `md5` | `{{ 'ansible' \| md5 }}` | MD5 hash |
| `normpath` | `{{ path \| normpath }}` | Normalize path |
| `password_hash` | `{{ 'secret' \| password_hash('sha512') }}` | Needs **passlib** on controller |
| `path_join` | `{{ parts \| path_join }}` | Join path components |
| `permutations` | `{{ list \| permutations(2) \| list }}` | n-permutations |
| `pow` | `{{ 2 \| pow(10) }}` | Exponentiation |
| `product` | `{{ a \| product(b) \| list }}` | Cartesian product |
| `quote` | `{{ 'hello world' \| quote }}` | Shell quoting |
| `random` | `{{ 100 \| random(10) }}` | Random int or list element |
| `realpath` | `{{ '/etc/hosts' \| realpath }}` | Resolve symlinks |
| `regex_escape` | `{{ 'file.txt' \| regex_escape }}` | Escape regex metacharacters |
| `regex_findall` | `{{ text \| regex_findall('pat') }}` | All matches |
| `regex_replace` | `{{ text \| regex_replace('pat', 'repl') }}` | Regex replace |
| `regex_search` | `{{ text \| regex_search('pat', '\\1') }}` | First match / capture |
| `rekey_on_member` | `{{ list \| rekey_on_member('key') }}` | Index list of dicts |
| `relpath` | `{{ path \| relpath('/var') }}` | Relative path |
| `root` | `{{ 27 \| root(3) }}` | nth root |
| `sha1` | `{{ 'ansible' \| sha1 }}` | SHA-1 hash |
| `shuffle` | `{{ list \| shuffle }}` | Randomize list |
| `split` | `{{ 'a,b' \| split(',') }}` | Split string |
| `splitext` | `{{ '/etc/foo.cfg' \| splitext }}` | Root + extension |
| `strftime` | `{{ '%Y-%m-%d' \| strftime(0) }}` | Format epoch seconds |
| `subelements` | `{{ hosts \| subelements(['ifaces']) }}` | Nested loop helper |
| `symmetric_difference` | `{{ a \| symmetric_difference(b) }}` | XOR of lists |
| `ternary` | `{{ cond \| ternary('yes', 'no') }}` | Inline if/else |
| `to_datetime` | `{{ '2026-06-26' \| to_datetime('%Y-%m-%d') }}` | Parse datetime |
| `to_json` | `{{ data \| to_json }}` | JSON serialize |
| `to_nice_json` | `{{ data \| to_nice_json }}` | Indented JSON |
| `to_nice_yaml` | `{{ data \| to_nice_yaml }}` | Indented YAML |
| `to_uuid` | `{{ 'host' \| to_uuid }}` | Namespaced UUID |
| `to_yaml` | `{{ data \| to_yaml }}` | YAML serialize |
| `type_debug` | `{{ data \| type_debug }}` | Show value type |
| `union` | `{{ a \| union(b) }}` | List union |
| `unique` | `{{ list \| unique }}` | Deduplicate |
| `unvault` | `{{ vaulted \| unvault('password') }}` | Decrypt vault blob |
| `urldecode` | `{{ 'a%20b' \| urldecode }}` | URL decode |
| `urlsplit` | `{{ url \| urlsplit }}` | URL components |
| `vault` | `{{ 'secret' \| vault('password') }}` | Encrypt inline |
| `win_basename` | `{{ win_path \| win_basename }}` | Windows base name |
| `win_dirname` | `{{ win_path \| win_dirname }}` | Windows directory |
| `win_splitdrive` | `{{ win_path \| win_splitdrive }}` | Split drive letter |
| `zip` | `{{ a \| zip(b) \| list }}` | Zip parallel lists |
| `zip_longest` | `{{ a \| zip_longest(b, fillvalue=0) }}` | Zip uneven lists |

You can omit the `ansible.builtin.` prefix in playbooks (`combine` instead of `ansible.builtin.combine`); this demo uses the fully qualified name for clarity.

## Expected failures (by design)

| Task | Why |
|------|-----|
| `mandatory` on undefined var | Demonstrates fail-fast behavior; play uses `ignore_errors: true` |
| `password_hash` | Requires `passlib` on the controller; skipped with `ignore_errors` if missing |

Install passlib to exercise `password_hash`:

```bash
pip install passlib
```

## Things to try

- Add files under `files/` and re-run to see `fileglob` results change.
- Export `DEMO_FILTER_VAR` before running to affect `expandvars`.
- Capture `vault` output from `set_fact` and reuse it in a group_var template.
- Compare `bool`, `ternary`, and Jinja2 truthiness pitfalls in [demo-when](../demo-when/README.md).

## How to run

```bash
cd demo-ansible-filters
ansible-playbook playbook.yml
```

Expected PLAY RECAP: `ok=71`, `ignored=2` (mandatory + password_hash when passlib is absent).

## Sample output (abbreviated)

```text
TASK [combine — merge dictionaries (recursive=True)] ***
ok: [localhost] => { "msg": {"app_port": 8080, "env": "staging", "owner": "platform"} }

TASK [vault — encrypt a string inline] ***************
ok: [localhost] => { "ansible_facts": {"demo_vault_blob": "$ANSIBLE_VAULT;1.1;AES256..."} }

TASK [unvault — decrypt a vaulted string] ************
ok: [localhost] => { "msg": "demo-secret" }

PLAY RECAP *******************************************
localhost : ok=71  changed=0  failed=0  ignored=2
```
