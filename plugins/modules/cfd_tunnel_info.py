#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel_info
short_description: Gather information about Cloudflare cloudflared tunnels
description:
  - Gather active Cloudflare cloudflared tunnels and optionally their connector tokens.
  - Results contain sensitive connector tokens when O(include_token=true); protect
    registered results and task output appropriately.
version_added: '2.0.0'
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
    default: false
    description:
      - Whether to retrieve and return each sensitive tunnel token.
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
  contains:
    id:
      description: Cloudflared tunnel identifier.
      returned: always
      type: str
    name:
      description: Cloudflared tunnel name.
      returned: always
      type: str
    token:
      description: Sensitive connector token.
      returned: when O(include_token=true)
      type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    cloudflare_query,
    get_result,
    list_all,
    resource_field,
    resource_id,
)


def list_resources(module, client):
    account_id = module.params["account_id"]
    cfd_tunnels = list_all(
        client,
        cloudflare_query(
            cloudflare_path("accounts", account_id, "cfd_tunnel"),
            {"is_deleted": "false"},
        ),
        per_page=1000,
    )

    for tunnel in cfd_tunnels:
        tunnel_id = resource_id(module, tunnel, "cloudflared tunnel")
        resource_field(module, tunnel, "name", "cloudflared tunnel")
        if module.params["include_token"]:
            token = get_result(
                client,
                cloudflare_path(
                    "accounts", account_id, "cfd_tunnel", tunnel_id, "token"
                ),
            )
            tunnel["token"] = resource_field(
                module,
                {"token": token},
                "token",
                "cloudflared tunnel token",
            )

    module.exit_json(changed=False, cfd_tunnels=cfd_tunnels)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "include_token": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
