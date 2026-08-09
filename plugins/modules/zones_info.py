#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: zones_info
short_description: Gather information about Cloudflare zones
description:
  - Gather Cloudflare zones visible to the supplied API token.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  match:
    type: str
    choices:
      - any
      - all
    default: all
    description:
      - Whether all or any supplied filters must match.
requirements:
  - python >= 3.9
  - cloudflare >= 5.6.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none

"""

EXAMPLES = r"""
- name: Gather zones
  linuxhq.cloudflare.zones_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
zones:
  description: Cloudflare zones.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Cloudflare zone identifier.
      returned: always
      type: str
    name:
      description: Fully qualified domain name of the zone.
      returned: always
      type: str
    status:
      description: Current zone activation status.
      returned: when available
      type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    cloudflare_query,
    list_all,
    validate_resource_fields,
)


def list_resources(module, client):
    zones = list_all(
        client,
        cloudflare_query(cloudflare_path("zones"), {"match": module.params["match"]}),
    )
    validate_resource_fields(module, zones, "id", "zone")

    module.exit_json(changed=False, zones=zones)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "match": {"type": "str", "choices": ["any", "all"], "default": "all"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
