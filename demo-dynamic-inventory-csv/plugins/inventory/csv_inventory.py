#!/usr/bin/env python3

from __future__ import annotations

import csv
import os

from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable


DOCUMENTATION = """
    name: csv_inventory
    short_description: Build inventory from a CSV file using YAML-defined filters
    description:
        - Reads hosts from a CSV file and assigns them to Ansible groups.
        - Row filters and group mappings are defined in each inventory source YAML file.
        - CSV columns are set as host variables, so O(keyed_groups) and O(groups) work like the
          C(community.vmware.vmware_vm_inventory) plugin.
    options:
        plugin:
            description: Inventory plugin name.
            required: true
            choices: ['csv_inventory']
        csv_file:
            description: Path to the CSV file. Relative paths resolve from the inventory YAML file.
            required: true
            type: str
        filters:
            description: Column filters. Each key is a CSV column; values are allowed values for that column.
            type: dict
            default: {}
        always_groups:
            description: Groups every matching host is added to. Omit or leave empty if not needed.
            type: list
            elements: str
            default: []
        flag_groups:
            description: Groups keyed by CSV boolean column names (TRUE/FALSE).
            type: dict
            default: {}
    extends_documentation_fragment:
      - constructed
"""

EXAMPLES = """
# Filter CSV rows and assign groups from YAML configuration
plugin: csv_inventory
csv_file: hosts.csv
filters:
  Cloud:
    - AWS
  Env:
    - DEV
    - QA
always_groups:
  - managed
keyed_groups:
  - prefix: region
    key: Region | lower
flag_groups:
  linux_team: LinuxTeam
  windows_team: WindowsTeam
"""


class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = 'csv_inventory'

    def verify_file(self, path):
        return super().verify_file(path) and path.endswith(('.yaml', 'yml'))

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache=cache)
        self._read_config_data(path)

        csv_file = self.get_option('csv_file')
        filters = self.get_option('filters') or {}
        always_groups = self.get_option('always_groups') or []
        flag_groups = self.get_option('flag_groups') or {}
        keyed_groups = self.get_option('keyed_groups') or []
        groups = self.get_option('groups') or {}
        compose = self.get_option('compose') or {}
        strict = self.get_option('strict') or False

        if not csv_file:
            raise AnsibleParserError('csv_file must be specified in the inventory source')

        csv_path = csv_file if os.path.isabs(csv_file) else os.path.normpath(
            os.path.join(os.path.dirname(path), csv_file)
        )
        if not os.path.isfile(csv_path):
            raise AnsibleParserError(f'CSV file not found: {csv_path}')

        with open(csv_path, newline='') as csv_handle:
            for row in csv.DictReader(csv_handle):
                if not self._row_matches(row, filters):
                    continue

                host = row['Host'].upper()
                host_vars = dict(row)

                self.inventory.add_host(host)
                for varname, value in host_vars.items():
                    self.inventory.set_variable(host, varname, value)

                for group in always_groups:
                    self.inventory.add_group(group)
                    self.inventory.add_host(host, group)

                for group, column in flag_groups.items():
                    if row.get(column, '').lower() == 'true':
                        self.inventory.add_group(group)
                        self.inventory.add_host(host, group)

                self._set_composite_vars(compose, host_vars, host, strict=strict)
                self._add_host_to_composed_groups(groups, host_vars, host, strict=strict)
                self._add_host_to_keyed_groups(keyed_groups, host_vars, host, strict=strict)

    @staticmethod
    def _row_matches(row, filters):
        for column, values in filters.items():
            if values and row.get(column) not in values:
                return False
        return True
