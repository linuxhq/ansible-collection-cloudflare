#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pagerules_info
short_description: Gather information about Cloudflare Page Rules
description:
  - Gather page rules for all accessible zones.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
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
- name: Gather page rules
  linuxhq.cloudflare.pagerules_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
pagerules:
  description: Page rules grouped by zone.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Cloudflare zone identifier.
      returned: always
      type: str
    name:
      description: Cloudflare zone name.
      returned: always
      type: str
    pagerules:
      description: Page rules configured for the zone.
      returned: always
      type: list
      elements: dict
      contains:
        id:
          description: Page rule identifier.
          returned: always
          type: str
        actions:
          description: Actions applied by the page rule.
          returned: always
          type: list
          elements: dict
        targets:
          description: Target constraints identifying the page rule.
          returned: always
          type: list
          elements: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    list_all,
    require_mapping,
    resource_field,
    resource_id,
    validate_resource_fields,
)


def list_resources(module, client):
    pagerules = []
    zones = list_all(client, "/zones")

    for zone in zones:
        zone_id = resource_id(module, zone, "zone")
        zone_name = resource_field(module, zone, "name", "zone")

        rules = list_all(
            client,
            cloudflare_path("zones", zone_id, "pagerules"),
        )
        validate_resource_fields(module, rules, "id", "page rule")
        for rule in rules:
            for field in ("actions", "targets"):
                values = rule.get(field)
                if not isinstance(values, list):
                    module.fail_json(msg="Cloudflare API returned malformed page rule data")
                for value in values:
                    require_mapping(module, value, f"page rule {field[:-1]}")

        pagerules.append(
            {
                "id": zone_id,
                "name": zone_name,
                "pagerules": rules,
            }
        )

    module.exit_json(changed=False, pagerules=pagerules)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
