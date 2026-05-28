#!/usr/bin/env bash
# Replace real hostnames with placeholders before commit.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
conf_file="${script_dir}/sanitize-hostname.conf"
example_file="${script_dir}/sanitize-hostname.conf.example"

if [[ ! -f "$conf_file" ]]; then
  echo "sanitize-hostname: no config found" >&2
  echo "sanitize-hostname: copy ${example_file} to ${conf_file} and set REAL_HOST" >&2
  exit 0
fi

# shellcheck source=/dev/null
source "$conf_file"

if [[ -z "${REAL_HOST:-}" || -z "${PLACEHOLDER:-}" ]]; then
  echo "sanitize-hostname: REAL_HOST and PLACEHOLDER must be set in ${conf_file}" >&2
  exit 1
fi

modified=0

for file in "$@"; do
  [[ -f "$file" ]] || continue
  if grep -qF "$REAL_HOST" "$file"; then
    sed -i "s|${REAL_HOST}|${PLACEHOLDER}|g" "$file"
    echo "sanitize-hostname: replaced hostname in ${file}" >&2
    modified=1
  fi
done

if (( modified )); then
  echo "sanitize-hostname: re-stage changed files and commit again" >&2
fi

exit 0
