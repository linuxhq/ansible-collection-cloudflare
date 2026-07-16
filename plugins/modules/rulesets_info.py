#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: rulesets_info
short_description: Gather information about cloudflare rulesets
description:
  - Gather a ruleset entrypoint phase for all accessible zones.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  phase:
    type: str
    default: http_request_firewall_custom
    description:
      - Ruleset phase.
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Gather rulesets
  linuxhq.cloudflare.rulesets_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
rulesets:
  description: Ruleset entrypoints grouped by zone.
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


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
        },
        supports_check_mode=True,
    )

    rulesets = []
    with cloudflare_client(module) as client:
        zones = list_all(client, "/zones")
        for zone in zones:
            if zone.get("id") is None:
                continue

            ruleset = get_result(
                client,
                "/zones/%s/rulesets/phases/%s/entrypoint"
                % (zone["id"], module.params["phase"]),
                default={},
                ok_statuses=[404],
            )

            rulesets.append(
                {
                    "id": ruleset.get("id"),
                    "name": zone.get("name"),
                    "phase": ruleset.get("phase"),
                    "rules": ruleset.get("rules") or [],
                    "zone_id": zone["id"],
                }
            )

    module.exit_json(changed=False, rulesets=rulesets)


if __name__ == "__main__":
    main()
