#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel_configurations_info
short_description: Gather information about cloudflared tunnel configurations
description:
  - Gather configurations for cloudflared tunnels in an account that have not been
    deleted.
  - A tunnel deleted while its configuration is being gathered is omitted.
  - Only remotely-managed tunnels are queried; locally-managed tunnel
    configurations are stored on the origin host.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
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
  contains:
    id:
      description: Cloudflared tunnel identifier.
      returned: always
      type: str
    name:
      description: Cloudflared tunnel name.
      returned: always
      type: str
    config:
      description: Remotely managed tunnel configuration.
      returned: always
      type: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    get_or_none,
    require_mapping,
    resource_list,
    serialize_resource,
)


def run(module, client):
    account_id = module.params["account_id"]
    tunnels = client.zero_trust.tunnels.cloudflared
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering cloudflared tunnels",
        account_id=account_id,
    ):
        listed = resource_list(
            module,
            tunnels.list(account_id=account_id, is_deleted=False, per_page=1000),
            "cloudflared tunnel",
            required_fields=("id", "name"),
        )

    configurations = []
    for tunnel in listed:
        if tunnel.get("remote_config") is False or tunnel.get("config_src") == "local":
            continue

        with cloudflare_error_context(
            "Cloudflare API request failed while gathering the tunnel configuration",
            account_id=account_id,
            tunnel_id=tunnel["id"],
        ):
            # Skip a tunnel deleted after it was listed, which returns 404. A
            # null configuration becomes an empty mapping, so None means 404.
            configuration = get_or_none(
                lambda tunnel_id: serialize_resource(tunnels.configurations.get(tunnel_id, account_id=account_id))
                or {},
                tunnel["id"],
            )

        if configuration is None:
            continue

        require_mapping(module, configuration, "tunnel configuration")
        config = configuration.get("config")
        if config is None:
            config = {}
        else:
            require_mapping(module, config, "tunnel configuration")

        configurations.append({"id": tunnel["id"], "name": tunnel["name"], "config": config})

    module.exit_json(changed=False, cfd_tunnel_configurations=configurations)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
