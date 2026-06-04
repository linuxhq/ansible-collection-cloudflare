#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cfd_tunnel_info
short_description: Gather information about cloudflare cfd tunnels
description:
- Gather active Cloudflare cloudflared tunnels and optionally their connector tokens.
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
  include_token:
    type: bool
    default: true
    description:
    - Include token.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Gather cloudflared tunnels
  linuxhq.cloudflare.cfd_tunnel_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
cfd_tunnels:
  description: Cloudflare cloudflared tunnels.
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
            "include_token": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )

    account_id = module.params["account_id"]
    with cloudflare_client(module) as client:
        cfd_tunnels = get_result(
            client,
            "/accounts/%s/cfd_tunnel?is_deleted=false" % account_id,
            default=[],
        )

        if module.params["include_token"]:
            for tunnel in cfd_tunnels:
                if tunnel.get("id") is not None:
                    tunnel["token"] = get_result(
                        client,
                        "/accounts/%s/cfd_tunnel/%s/token" % (account_id, tunnel["id"]),
                    )

    module.exit_json(changed=False, cfd_tunnels=cfd_tunnels)


if __name__ == "__main__":
    main()
