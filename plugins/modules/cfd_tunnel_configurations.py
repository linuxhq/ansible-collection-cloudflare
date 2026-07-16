#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cfd_tunnel_configurations
short_description: Manage cloudflare cfd tunnel configurations
description:
  - Update the remotely managed configuration for a cloudflared tunnel.
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
      - Tunnel id.
  config:
    required: true
    type: dict
    description:
      - Config.
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5

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
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    get_result,
    normalize_current_by_desired_fields,
    put_result,
    values_differ,
)


def endpoint(account_id, tunnel_id):
    return "/accounts/%s/cfd_tunnel/%s/configurations" % (account_id, tunnel_id)


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

    params = module.params
    with cloudflare_client(module) as client:
        current = get_result(
            client,
            endpoint(params["account_id"], params["tunnel_id"]),
            default={},
        )

        current_config = current.get("config", {}) if isinstance(current, dict) else {}

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
        module.exit_json(
            changed=True,
            message="Tunnel configuration updated",
            configuration=configuration,
        )


if __name__ == "__main__":
    main()
