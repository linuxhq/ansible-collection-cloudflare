#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cfd_tunnel_configurations_info
short_description: Gather information about cloudflare cfd tunnel configurations
description:
- Gather configurations for active cloudflared tunnels in an account.
author:
- Taylor Kimball (@tkimball83)
options:
  account_id:
    required: true
    type: str
    description:
    - Cloudflare account identifier.
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
- name: Gather cloudflared tunnel configurations
  linuxhq.cloudflare.cfd_tunnel_configurations_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
cfd_tunnel_configurations:
  description: Cloudflare tunnel configurations.
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
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    account_id = module.params["account_id"]
    configurations = []
    with cloudflare_client(module) as client:
        tunnels = get_result(
            client,
            "/accounts/%s/cfd_tunnel?is_deleted=false" % account_id,
            default=[],
        )
        for tunnel in tunnels:
            if tunnel.get("id") is None:
                continue

            configuration = get_result(
                client,
                "/accounts/%s/cfd_tunnel/%s/configurations"
                % (account_id, tunnel["id"]),
                default={},
            )

            configurations.append(
                {
                    "id": tunnel["id"],
                    "name": tunnel.get("name"),
                    "config": configuration.get("config", {}),
                }
            )

    module.exit_json(changed=False, cfd_tunnel_configurations=configurations)


if __name__ == "__main__":
    main()
