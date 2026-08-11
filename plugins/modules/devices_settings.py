#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: devices_settings
short_description: Manage Cloudflare device settings
description:
  - Manage account-wide Cloudflare Zero Trust device settings.
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
  disable_for_time:
    type: float
    default: 0
    description:
      - Number of seconds users may temporarily disable the WARP client.
  gateway_proxy_enabled:
    type: bool
    default: false
    description:
      - Whether the WARP client proxies TCP traffic through Gateway.
  gateway_udp_proxy_enabled:
    type: bool
    default: false
    description:
      - Whether the WARP client proxies UDP traffic through Gateway.
  root_certificate_installation_enabled:
    type: bool
    default: false
    description:
      - Whether users may install the Cloudflare root certificate.
  use_zt_virtual_ip:
    type: bool
    default: false
    description:
      - Whether devices receive a Zero Trust virtual IP address.
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
  contains:
    gateway_proxy_enabled:
      description: Whether the WARP client proxies TCP traffic through Gateway.
      returned: when available
      type: bool
    gateway_udp_proxy_enabled:
      description: Whether the WARP client proxies UDP traffic through Gateway.
      returned: when available
      type: bool
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
    patch_result,
    payload_from_params,
    require_mapping,
    select_fields,
    validate_requested_values,
    values_differ,
)

FIELDS = (
    "disable_for_time",
    "gateway_proxy_enabled",
    "gateway_udp_proxy_enabled",
    "root_certificate_installation_enabled",
    "use_zt_virtual_ip",
)


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "devices", "settings")


def ensure_present(module, client):
    params = module.params

    payload = payload_from_params(params, FIELDS)

    current = get_result(client, endpoint(params["account_id"]), default={})
    require_mapping(module, current, "device settings")

    if not values_differ(select_fields(current, payload.keys()), payload):
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

    settings = patch_result(client, endpoint(params["account_id"]), payload)
    validate_requested_values(module, settings, payload, "device settings")
    module.exit_json(
        changed=True,
        message="Device settings updated",
        devices_settings=settings,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "disable_for_time": {"type": "float", "default": 0},
            "gateway_proxy_enabled": {"type": "bool", "default": False},
            "gateway_udp_proxy_enabled": {"type": "bool", "default": False},
            "root_certificate_installation_enabled": {"type": "bool", "default": False},
            "use_zt_virtual_ip": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        ensure_present(module, client)


if __name__ == "__main__":
    main()
