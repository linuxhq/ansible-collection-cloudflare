#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

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
- cloudflare >= 4.3.1, < 5

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
)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    pagerules = []
    with cloudflare_client(module) as client:
        zones = get_result(client, "/zones?per_page=1000", default=[])
        for zone in zones:
            if zone.get("id") is None:
                continue
            rules = get_result(
                client,
                "/zones/%s/pagerules" % zone["id"],
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


if __name__ == "__main__":
    main()
