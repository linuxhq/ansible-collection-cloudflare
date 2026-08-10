#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rulesets_info
short_description: Gather information about Cloudflare rulesets
description:
  - Gather a ruleset entrypoint phase for all accessible zones.
version_added: '2.0.0'
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
      - Cloudflare request phase whose entrypoint ruleset is returned.
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
  contains:
    id:
      description: Entrypoint ruleset identifier.
      returned: when a ruleset exists
      type: str
    name:
      description: Cloudflare zone name.
      returned: when available
      type: str
    phase:
      description: Cloudflare request phase controlled by the ruleset.
      returned: when a ruleset exists
      type: str
    rules:
      description: Ordered rules in the entrypoint ruleset.
      returned: always
      type: list
      elements: dict
    zone_id:
      description: Cloudflare zone identifier.
      returned: always
      type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    get_result,
    list_all,
    resource_id,
)


def list_resources(module, client):
    rulesets = []
    zones = list_all(client, "/zones")

    for zone in zones:
        zone_id = resource_id(module, zone, "zone")

        ruleset = get_result(
            client,
            cloudflare_path(
                "zones",
                zone_id,
                "rulesets",
                "phases",
                module.params["phase"],
                "entrypoint",
            ),
            default=None,
            ok_statuses=[404],
        )
        ruleset_id = None
        if ruleset is not None:
            ruleset_id = resource_id(module, ruleset, "ruleset")

        rulesets.append(
            {
                "id": ruleset_id,
                "name": zone.get("name"),
                "phase": ruleset.get("phase") if ruleset else None,
                "rules": ruleset.get("rules") or [] if ruleset else [],
                "zone_id": zone_id,
            }
        )

    module.exit_json(changed=False, rulesets=rulesets)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
