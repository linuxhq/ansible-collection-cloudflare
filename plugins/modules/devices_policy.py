#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: devices_policy
short_description: Manage cloudflare devices policy
description:
- Patch the Cloudflare Zero Trust default device policy for an account.
author:
- Taylor Kimball (@tkimball83)
options:
  account_id:
    required: true
    type: str
    description:
    - Cloudflare account identifier.
  allow_mode_switch:
    type: bool
    description:
    - Whether to allow the user to switch WARP between modes.
  allow_updates:
    type: bool
    description:
    - Whether to receive WARP client update notifications.
  allowed_to_leave:
    type: bool
    description:
    - Whether to allow devices to leave the organization.
  api_token:
    required: true
    type: str
    description:
    - Cloudflare API token.
  auto_connect:
    type: float
    description:
    - Seconds before reconnecting after WARP has been disabled.
  captive_portal:
    type: float
    description:
    - Seconds before turning on captive portal handling.
  disable_auto_fallback:
    type: bool
    description:
    - Whether to disable automatic fallback DNS resolver selection.
  exclude:
    type: list
    elements: dict
    description:
    - Split tunnel routes excluded from the WARP tunnel.
  exclude_office_ips:
    type: bool
    description:
    - Whether to add Microsoft IPs to split tunnel exclusions.
  include:
    type: list
    elements: dict
    description:
    - Split tunnel routes included in the WARP tunnel.
  lan_allow_minutes:
    type: float
    description:
    - Minutes a user is allowed access to their LAN.
  lan_allow_subnet_size:
    type: float
    description:
    - Subnet size for local access.
  register_interface_ip_with_dns:
    type: bool
    description:
    - Whether the operating system registers WARP's local interface IP with DNS.
  sccm_vpn_boundary_support:
    type: bool
    description:
    - Whether the WARP client indicates to SCCM that it is inside a VPN boundary.
  service_mode_v2:
    type: dict
    description:
    - WARP client service mode configuration.
  support_url:
    type: str
    description:
    - URL launched by the WARP client Send Feedback button.
  switch_locked:
    type: bool
    description:
    - Whether to allow the user to turn off WARP and disconnect the client.
  tunnel_protocol:
    type: str
    description:
    - Tunnel protocol to use.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Manage device policy
  linuxhq.cloudflare.devices_policy:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    allow_updates: true
    auto_connect: 60
    include:
      - address: 100.64.0.0/10
    service_mode_v2:
      mode: warp_tunnel_only
"""

RETURN = r"""
---
devices_policy:
  description: Cloudflare device policy.
  returned: when available
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
    patch_result,
    payload_from_params,
    values_differ,
)

FIELDS = (
    "allow_mode_switch",
    "allow_updates",
    "allowed_to_leave",
    "auto_connect",
    "captive_portal",
    "disable_auto_fallback",
    "exclude",
    "exclude_office_ips",
    "include",
    "lan_allow_minutes",
    "lan_allow_subnet_size",
    "register_interface_ip_with_dns",
    "sccm_vpn_boundary_support",
    "service_mode_v2",
    "support_url",
    "switch_locked",
    "tunnel_protocol",
)


def endpoint(account_id):
    return "/accounts/%s/devices/policy" % account_id


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "allow_mode_switch": {"type": "bool"},
            "allow_updates": {"type": "bool"},
            "allowed_to_leave": {"type": "bool"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "auto_connect": {"type": "float"},
            "captive_portal": {"type": "float"},
            "disable_auto_fallback": {"type": "bool"},
            "exclude": {"type": "list", "elements": "dict"},
            "exclude_office_ips": {"type": "bool"},
            "include": {"type": "list", "elements": "dict"},
            "lan_allow_minutes": {"type": "float"},
            "lan_allow_subnet_size": {"type": "float"},
            "register_interface_ip_with_dns": {"type": "bool"},
            "sccm_vpn_boundary_support": {"type": "bool"},
            "service_mode_v2": {"type": "dict"},
            "support_url": {"type": "str"},
            "switch_locked": {"type": "bool"},
            "tunnel_protocol": {"type": "str"},
        },
        mutually_exclusive=[("exclude", "include")],
        supports_check_mode=True,
    )

    params = module.params
    payload = payload_from_params(params, FIELDS)
    if not payload:
        module.exit_json(changed=False, message="No device policy fields provided")

    with cloudflare_client(module) as client:
        current = get_result(client, endpoint(params["account_id"]), default={})

        if not values_differ(
            normalize_current_by_desired_fields(current, payload),
            payload,
        ):
            module.exit_json(
                changed=False,
                message="Device policy already present",
                devices_policy=current,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Device policy would be updated",
                devices_policy=current,
            )

        policy = patch_result(client, endpoint(params["account_id"]), payload)
        module.exit_json(
            changed=True,
            message="Device policy updated",
            devices_policy=policy,
        )


if __name__ == "__main__":
    main()
