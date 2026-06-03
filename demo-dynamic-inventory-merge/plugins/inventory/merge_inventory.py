#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess

from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin


DOCUMENTATION = """
    name: merge_inventory
    short_description: Merge multiple flat inventory sources with last-wins precedence
    description:
        - Combines an ordered list of inventory sources into one inventory.
        - Later sources override conflicting variables from earlier sources, matching
          Ansible's normal multi-inventory precedence rules.
        - Each source may use any format Ansible accepts for C(ansible-inventory) C(-i)
          (INI, YAML, JSON, directories, and so on).
    options:
        plugin:
            description: Inventory plugin name.
            required: true
            choices: ['merge_inventory']
        sources:
            description:
                - Ordered inventory sources to merge.
                - List order is precedence order; later entries win on conflicts.
            required: true
            type: list
            elements: str
"""

EXAMPLES = """
# Merge INI, YAML, and JSON sources (paths relative to this inventory YAML file)
plugin: merge_inventory
sources:
  - sources/01-base.ini
  - sources/02-overrides.yaml
  - sources/03-final.json
"""


class InventoryModule(BaseInventoryPlugin):
    NAME = 'merge_inventory'

    def verify_file(self, path):
        return super().verify_file(path) and path.endswith(('.yaml', 'yml'))

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache=cache)
        self._read_config_data(path)

        sources = self.get_option('sources') or []
        if not sources:
            raise AnsibleParserError('sources must be specified in the inventory source')

        base_dir = os.path.dirname(path)
        resolved_sources = []
        for source in sources:
            source_path = source if os.path.isabs(source) else os.path.normpath(
                os.path.join(base_dir, source)
            )
            if not os.path.exists(source_path):
                raise AnsibleParserError(f'Inventory source not found: {source_path}')
            resolved_sources.append(source_path)

        merged = self._load_merged_inventory(resolved_sources)
        self._import_inventory_list(merged)

    def _load_merged_inventory(self, sources):
        command = ['ansible-inventory', '--list']
        for source in sources:
            command.extend(['-i', source])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise AnsibleParserError(
                'ansible-inventory was not found in PATH; install Ansible before using merge_inventory'
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise AnsibleParserError(exc.stderr or exc.stdout or str(exc)) from exc

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AnsibleParserError(
                f'ansible-inventory returned invalid JSON: {exc}'
            ) from exc

    def _import_inventory_list(self, data):
        hostvars = data.get('_meta', {}).get('hostvars', {})
        group_names = [
            name for name, value in data.items()
            if name != '_meta' and isinstance(value, dict)
        ]

        for group_name in group_names:
            self.inventory.add_group(group_name)

        for group_name in group_names:
            group_data = data[group_name]
            for varname, value in group_data.get('vars', {}).items():
                self.inventory.set_variable(group_name, varname, value)

            for child in group_data.get('children', []):
                self.inventory.add_group(child)
                self.inventory.add_child(group_name, child)

            for host in group_data.get('hosts', []):
                self.inventory.add_host(host, group_name)
                for varname, value in hostvars.get(host, {}).items():
                    self.inventory.set_variable(host, varname, value)
