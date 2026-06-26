# demo-jinja2-filters — Jinja2 built-in filter reference

Runnable examples of every **Jinja2 built-in filter** (54 total, including aliases) that Ansible templates can use. Each task prints one filter expression and its result.

Ansible also ships **ansible.builtin** filters (see [demo-ansible-filters](../demo-ansible-filters/README.md)); those are separate from the stock Jinja2 filters covered here.

## What this shows

| Concept | Where it lives |
|---------|----------------|
| Sample data | Play `vars` in [`playbook.yml`](playbook.yml) |
| One task per filter | Grouped by category (math, strings, sequences, …) |
| AAP entry point | [`playbook-aap.yml`](playbook-aap.yml) imports the CLI playbook |

Filters run entirely on the controller during templating — no remote hosts or fact gathering required.

## Filter index

Aliases are shown once; use the alias interchangeably in templates.

| Filter | Alias | Example expression | Typical use |
|--------|-------|-------------------|-------------|
| `abs` | | `{{ -17 \| abs }}` | Absolute value |
| `attr` | | `{{ 'ansible' \| attr('upper')() }}` | Dynamic attribute/method access |
| `batch` | | `{{ list \| batch(3) \| list }}` | Fixed-size sublists |
| `capitalize` | | `{{ 'hELLO' \| capitalize }}` | First letter upper |
| `center` | | `{{ 'ansible' \| center(15) }}` | Pad to width |
| `count` | `length` | `{{ list \| length }}` | Item count |
| `d` | `default` | `{{ var \| default('fallback') }}` | Undefined fallback |
| `dictsort` | | `{{ dict \| dictsort }}` | Sort dict items by key |
| `e` | `escape` | `{{ '<tag>' \| escape }}` | HTML escape |
| `filesizeformat` | | `{{ 1536000 \| filesizeformat }}` | Human-readable bytes |
| `first` | | `{{ list \| first }}` | First element |
| `float` | | `{{ '3.14' \| float }}` | Cast to float |
| `forceescape` | | `{{ safe_str \| forceescape }}` | Escape even if marked safe |
| `format` | | `{{ '%s=%d' \| format('port', 8080) }}` | printf-style format |
| `groupby` | | `{{ users \| groupby('role') }}` | Group objects by attribute |
| `indent` | | `{{ text \| indent(2) }}` | Indent multiline text |
| `int` | | `{{ '42' \| int }}` | Cast to integer |
| `items` | | `{{ dict \| items \| list }}` | Key/value pairs for loops |
| `join` | | `{{ list \| join(', ') }}` | Join sequence to string |
| `last` | | `{{ list \| last }}` | Last element |
| `length` | `count` | `{{ list \| length }}` | Item count |
| `list` | | `{{ 'abc' \| list }}` | Iterable → list |
| `lower` | | `{{ 'Ansible' \| lower }}` | Lowercase |
| `map` | | `{{ names \| map('upper') \| list }}` | Apply filter per item |
| `max` | | `{{ list \| max }}` | Maximum value |
| `min` | | `{{ list \| min }}` | Minimum value |
| `pprint` | | `{{ data \| pprint }}` | Pretty-print for debug |
| `random` | | `{{ list \| random }}` | Random element |
| `reject` | | `{{ list \| reject('equalto', 1) }}` | Drop matching items |
| `rejectattr` | | `{{ users \| rejectattr('role', 'eq', 'admin') }}` | Drop objects by attribute |
| `replace` | | `{{ 'a-b' \| replace('-', '_') }}` | Substring replace |
| `reverse` | | `{{ list \| reverse \| list }}` | Reverse order |
| `round` | | `{{ 3.14159 \| round(2) }}` | Round number |
| `safe` | | `{{ html \| safe }}` | Mark HTML safe |
| `select` | | `{{ list \| select('gt', 4) }}` | Keep matching items |
| `selectattr` | | `{{ users \| selectattr('role', 'eq', 'admin') }}` | Keep objects by attribute |
| `slice` | | `{{ list \| slice(3) \| list }}` | Chunk into columns |
| `sort` | | `{{ list \| sort }}` | Sort sequence |
| `string` | | `{{ 42 \| string }}` | Coerce to string |
| `striptags` | | `{{ html \| striptags }}` | Strip HTML tags |
| `sum` | | `{{ list \| sum(start=100) }}` | Sum numbers |
| `title` | | `{{ 'hello world' \| title }}` | Title case |
| `tojson` | | `{{ dict \| tojson }}` | JSON string |
| `trim` | | `{{ '  x  ' \| trim }}` | Strip whitespace |
| `truncate` | | `{{ long \| truncate(12, True, '...') }}` | Shorten with ellipsis |
| `unique` | | `{{ list \| unique \| list }}` | Deduplicate |
| `upper` | | `{{ 'ansible' \| upper }}` | Uppercase |
| `urlencode` | | `{{ 'a b' \| urlencode }}` | Percent-encode |
| `urlize` | | `{{ text \| urlize }}` | Linkify URLs in text |
| `wordcount` | | `{{ 'one two' \| wordcount }}` | Count words |
| `wordwrap` | | `{{ text \| wordwrap(12) }}` | Wrap lines |
| `xmlattr` | | `{{ attrs \| xmlattr }}` | Build HTML/XML attributes |

## Jinja2 vs Ansible filters

Several names exist in both worlds (for example `default`, `join`, `unique`). In Ansible playbooks, **ansible.builtin filters take precedence** when names collide. This demo uses expressions that exercise the Jinja2 implementations; for Ansible-specific behavior see [demo-ansible-filters](../demo-ansible-filters/README.md).

## Things to try

- Change `sample_list` or `sample_users` in `vars` and re-run to see `map`, `selectattr`, and `groupby` output change.
- Set `unset_jinja_var` in extra vars (`-e unset_jinja_var=provided`) and compare the `default` filter result.
- Pipe survey answers through `| bool` when you need real booleans — Jinja2 truthiness treats the string `"false"` as true (see [demo-when](../demo-when/README.md)).

## How to run

```bash
cd demo-jinja2-filters
ansible-playbook playbook.yml
```

Expected PLAY RECAP: `ok=51`, `failed=0`.

## Sample output (abbreviated)

```text
TASK [abs — absolute value] ************************
ok: [localhost] => { "msg": "17" }

TASK [map — apply filter or attribute to each item]
ok: [localhost] => { "msg": ["ALICE", "BOB", "CAROL"] }

TASK [groupby — group items by attribute] **********
ok: [localhost] => { "msg": [[...admin...], [...user...]] }

PLAY RECAP *****************************************
localhost : ok=51  changed=0  failed=0  skipped=0
```
