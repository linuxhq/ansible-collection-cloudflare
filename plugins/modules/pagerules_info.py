#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pagerules_info
short_description: Gather information about cloudflare pagerules
description:
  - Gather page rules for all accessible zones.
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

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    get_result,
    list_all,
)


def list(module, client):
    pagerules = []
    zones = list_all(client, "/zones")

    for zone in zones:
        if zone.get("id") is None:
            continue

        rules = get_result(
            client,
            "/zones/{}/pagerules".format(zone["id"]),
            default=[],
        )

        pagerules.append(
            {
                "id": zone["id"],
                "name": zone.get("name"),
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
        list(module, client)


if __name__ == "__main__":
    main()
