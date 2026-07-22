#!/usr/bin/env bash
# Replace sensitive strings with placeholders before commit.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
conf_file="${script_dir}/sanitize-strings.conf"
example_file="${script_dir}/sanitize-strings.conf.example"

escape_sed_replacement() {
  printf '%s' "$1" | sed -e 's/[\\/&|]/\\&/g'
}

if [[ ! -f "$conf_file" ]]; then
  echo "sanitize-strings: no config found" >&2
  echo "sanitize-strings: copy ${example_file} to ${conf_file} and add old:new pairs" >&2
  exit 0
fi

replacements=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line#"${line%%[![:space:]]*}"}"    # trim leading whitespace
  line="${line%"${line##*[![:space:]]}"}"    # trim trailing whitespace
  [[ -z "$line" || "$line" == \#* ]] && continue

  if [[ "$line" != *:* ]]; then
    echo "sanitize-strings: invalid line (expected old:new): ${line}" >&2
    exit 1
  fi

  old="${line%%:*}"
  new="${line#*:}"
  if [[ -z "$old" ]]; then
    echo "sanitize-strings: empty old string in line: ${line}" >&2
    exit 1
  fi

  replacements+=("${old}|${new}")
done < "$conf_file"

if ((${#replacements[@]} == 0)); then
  echo "sanitize-strings: no replacements defined in ${conf_file}" >&2
  exit 1
fi

modified=0

for file in "$@"; do
  [[ -f "$file" ]] || continue
  file_modified=0

  for pair in "${replacements[@]}"; do
    old="${pair%%|*}"
    new="${pair#*|}"
    if grep -qF "$old" "$file"; then
      old_esc="$(escape_sed_replacement "$old")"
      new_esc="$(escape_sed_replacement "$new")"
      sed -i "s|${old_esc}|${new_esc}|g" "$file"
      echo "sanitize-strings: replaced '${old}' in ${file}" >&2
      file_modified=1
    fi
  done

  (( file_modified )) && modified=1
done

if (( modified )); then
  echo "sanitize-strings: re-stage changed files and commit again" >&2
  exit 1
fi

exit 0
