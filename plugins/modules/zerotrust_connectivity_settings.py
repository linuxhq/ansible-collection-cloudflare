#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: zerotrust_connectivity_settings
short_description: Manage cloudflare zerotrust connectivity settings
description:
- Manage Cloudflare Zero Trust connectivity settings for an account.
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
  icmp_proxy_enabled:
    type: bool
    default: false
    description:
    - Icmp proxy enabled.
  offramp_warp_enabled:
    type: bool
    default: false
    description:
    - Offramp warp enabled.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Manage Zero Trust connectivity settings
  linuxhq.cloudflare.zerotrust_connectivity_settings:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    icmp_proxy_enabled: true
"""

RETURN = r"""
---
connectivity_settings:
  description: Cloudflare Zero Trust connectivity settings.
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
    patch_result,
    payload_from_params,
    selected_values_differ,
)

FIELDS = ("icmp_proxy_enabled", "offramp_warp_enabled")


def endpoint(account_id):
    return "/accounts/%s/zerotrust/connectivity_settings" % account_id


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "icmp_proxy_enabled": {"type": "bool", "default": False},
            "offramp_warp_enabled": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    params = module.params
    payload = payload_from_params(params, FIELDS)
    with cloudflare_client(module) as client:
        current = get_result(client, endpoint(params["account_id"]), default={})
        if not selected_values_differ(current, payload, FIELDS):
            module.exit_json(
                changed=False,
                message="Connectivity settings already present",
                connectivity_settings=current,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Connectivity settings would be updated",
                connectivity_settings=current,
            )

        settings = patch_result(client, endpoint(params["account_id"]), payload)
        module.exit_json(
            changed=True,
            message="Connectivity settings updated",
            connectivity_settings=settings,
        )


if __name__ == "__main__":
    main()
