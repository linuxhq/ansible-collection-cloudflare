#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel_configurations
short_description: Manage Cloudflare cloudflared tunnel configurations
description:
  - Update the remotely managed configuration for a cloudflared tunnel.
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
  tunnel_id:
    required: true
    type: str
    description:
      - Cloudflared tunnel identifier.
  config:
    required: true
    type: dict
    description:
      - Complete remotely managed tunnel configuration.
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
- name: Configure a cloudflared tunnel
  linuxhq.cloudflare.cfd_tunnel_configurations:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    tunnel_id: "{{ tunnel_id }}"
    config:
      ingress:
        - service: http_status:404
"""

RETURN = r"""
---
configuration:
  description: Cloudflare tunnel configuration.
  returned: always
  type: dict
  contains:
    config:
      description: Remotely managed tunnel configuration.
      returned: always
      type: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    get_result,
    normalize_current_by_desired_fields,
    put_result,
    require_mapping,
    values_differ,
)


def endpoint(account_id, tunnel_id):
    return cloudflare_path("accounts", account_id, "cfd_tunnel", tunnel_id, "configurations")


def ensure_present(module, client):
    params = module.params

    current = get_result(
        client,
        endpoint(params["account_id"], params["tunnel_id"]),
        default={},
    )
    require_mapping(module, current, "tunnel configuration")
    current_config = current.get("config")
    if current_config is None:
        current_config = {}
    else:
        require_mapping(module, current_config, "tunnel configuration")

    if not values_differ(
        normalize_current_by_desired_fields(current_config, params["config"]),
        params["config"],
    ):
        module.exit_json(
            changed=False,
            message="Tunnel configuration already present",
            configuration=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Tunnel configuration would be updated",
            configuration=current,
        )

    configuration = put_result(
        client,
        endpoint(params["account_id"], params["tunnel_id"]),
        {"config": params["config"]},
    )
    require_mapping(module, configuration, "tunnel configuration")
    returned_config = configuration.get("config")
    require_mapping(module, returned_config, "tunnel configuration")
    if values_differ(
        normalize_current_by_desired_fields(returned_config, params["config"]),
        params["config"],
    ):
        module.fail_json(msg="Cloudflare did not apply the tunnel configuration")
    module.exit_json(
        changed=True,
        message="Tunnel configuration updated",
        configuration=configuration,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "tunnel_id": {"required": True, "type": "str"},
            "config": {"required": True, "type": "dict"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        ensure_present(module, client)


if __name__ == "__main__":
    main()
