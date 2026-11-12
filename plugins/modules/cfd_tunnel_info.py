#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel_info
short_description: Gather information about Cloudflare cloudflared tunnels
description:
  - Gather Cloudflare cloudflared tunnels that have not been deleted, and optionally
    their connector tokens.
  - Results contain sensitive connector tokens when O(include_token=true); protect
    registered results and task output appropriately.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  include_token:
    type: bool
    default: false
    description:
      - Whether to retrieve and return each sensitive tunnel token.
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
    cloudflare_error_context,
    resource_field,
    resource_list,
)


def run(module, client):
    account_id = module.params["account_id"]
    tunnels = client.zero_trust.tunnels.cloudflared
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering cloudflared tunnels",
        account_id=account_id,
    ):
        cfd_tunnels = resource_list(
            module,
            tunnels.list(account_id=account_id, is_deleted=False, per_page=1000),
            "cloudflared tunnel",
            required_fields=("id", "name"),
        )

    if module.params["include_token"]:
        for tunnel in cfd_tunnels:
            with cloudflare_error_context(
                "Cloudflare API request failed while gathering the cloudflared tunnel token",
                account_id=account_id,
                resource_id=tunnel["id"],
            ):
                token = tunnels.token.get(tunnel["id"], account_id=account_id)

            tunnel["token"] = resource_field(module, {"token": token}, "token", "cloudflared tunnel token")

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
        run(module, client)


if __name__ == "__main__":
    main()
