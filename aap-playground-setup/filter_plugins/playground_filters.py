"""Playground CaC Jinja2 filters."""

from __future__ import annotations

from ansible.template import AnsibleUndefined


def _is_blank(value: object) -> bool:
    if value is None or isinstance(value, AnsibleUndefined):
        return True
    return str(value).strip() == ""


def playground_nonempty(value: object) -> str | None:
    """Return trimmed text, or None when value is blank (use with | default(omit))."""
    if _is_blank(value):
        return None
    return str(value).strip()


def playground_sanitize_credential_inputs(inputs: object) -> dict | None:
    """Drop blank input values so CaC does not send empty secrets to the API."""
    if not isinstance(inputs, dict):
        return None
    cleaned = {
        key: value
        for key, value in inputs.items()
        if not _is_blank(value)
    }
    return cleaned or None


class FilterModule:
    def filters(self):
        return {
            "playground_nonempty": playground_nonempty,
            "playground_sanitize_credential_inputs": playground_sanitize_credential_inputs,
        }
