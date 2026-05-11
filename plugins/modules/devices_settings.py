#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: devices_settings
short_description: Manage Cloudflare Zero Trust device settings
description:
- Manage account-wide Cloudflare Zero Trust device settings.
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
  disable_for_time:
    type: int
    default: 0
    description:
    - Disable for time.
  gateway_proxy_enabled:
    type: bool
    default: false
    description:
    - Gateway proxy enabled.
  gateway_udp_proxy_enabled:
    type: bool
    default: false
    description:
    - Gateway udp proxy enabled.
  root_certificate_installation_enabled:
    type: bool
    default: false
    description:
    - Root certificate installation enabled.
  use_zt_virtual_ip:
    type: bool
    default: false
    description:
    - Use zt virtual ip.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Manage device settings
  linuxhq.cloudflare.devices_settings:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    gateway_proxy_enabled: true
"""

RETURN = r"""
---
devices_settings:
  description: Cloudflare device settings.
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
    payload_from_params,
    put_result,
    selected_values_differ,
)

FIELDS = (
    "disable_for_time",
    "gateway_proxy_enabled",
    "gateway_udp_proxy_enabled",
    "root_certificate_installation_enabled",
    "use_zt_virtual_ip",
)


def endpoint(account_id):
    return "/accounts/%s/devices/settings" % account_id


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "disable_for_time": {"type": "int", "default": 0},
            "gateway_proxy_enabled": {"type": "bool", "default": False},
            "gateway_udp_proxy_enabled": {"type": "bool", "default": False},
            "root_certificate_installation_enabled": {"type": "bool", "default": False},
            "use_zt_virtual_ip": {"type": "bool", "default": False},
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
                message="Device settings already present",
                devices_settings=current,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Device settings would be updated",
                devices_settings=current,
            )

        settings = put_result(client, endpoint(params["account_id"]), payload)
        module.exit_json(
            changed=True,
            message="Device settings updated",
            devices_settings=settings,
        )


if __name__ == "__main__":
    main()
