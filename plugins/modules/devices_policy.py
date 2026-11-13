#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: devices_policy
short_description: Manage the Cloudflare device policy
description:
  - Patch the Cloudflare Zero Trust default device policy for an account.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  allow_mode_switch:
    type: bool
    description:
      - Whether to allow the user to switch WARP between modes.
      - When omitted, the current value is left unchanged.
  allow_updates:
    type: bool
    description:
      - Whether to receive WARP client update notifications.
      - When omitted, the current value is left unchanged.
  allowed_to_leave:
    type: bool
    description:
      - Whether to allow devices to leave the organization.
      - When omitted, the current value is left unchanged.
  auto_connect:
    type: float
    description:
      - Seconds before reconnecting after WARP has been disabled.
      - When omitted, the current value is left unchanged.
  captive_portal:
    type: float
    description:
      - Seconds before turning on captive portal handling.
      - When omitted, the current value is left unchanged.
  disable_auto_fallback:
    type: bool
    description:
      - Whether to disable automatic fallback DNS resolver selection.
      - When omitted, the current value is left unchanged.
  exclude:
    type: list
    elements: dict
    description:
      - Split tunnel routes excluded from the WARP tunnel.
      - When omitted, the current value is left unchanged.
      - Mutually exclusive with O(include).
  exclude_office_ips:
    type: bool
    description:
      - Whether to add Microsoft IPs to split tunnel exclusions.
      - When omitted, the current value is left unchanged.
  include:
    type: list
    elements: dict
    description:
      - Split tunnel routes included in the WARP tunnel.
      - When omitted, the current value is left unchanged.
      - Mutually exclusive with O(exclude).
  lan_allow_minutes:
    type: float
    description:
      - Minutes a user is allowed access to their LAN.
      - When omitted, the current value is left unchanged.
  lan_allow_subnet_size:
    type: float
    description:
      - Subnet size for local access.
      - When omitted, the current value is left unchanged.
  register_interface_ip_with_dns:
    type: bool
    description:
      - Whether the operating system registers WARP's local interface IP with DNS.
      - When omitted, the current value is left unchanged.
  sccm_vpn_boundary_support:
    type: bool
    description:
      - Whether the WARP client indicates to SCCM that it is inside a VPN boundary.
      - When omitted, the current value is left unchanged.
  service_mode_v2:
    type: dict
    description:
      - WARP client service mode configuration.
      - When omitted, the current value is left unchanged.
  support_url:
    type: str
    description:
      - URL launched by the WARP client Send Feedback button.
      - When omitted, the current value is left unchanged.
  switch_locked:
    type: bool
    description:
      - Whether to prevent users from turning off WARP and disconnecting the client.
      - When omitted, the current value is left unchanged.
  tunnel_protocol:
    type: str
    description:
      - Tunnel protocol to use.
      - When omitted, the current value is left unchanged.
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
  returned: always
  type: dict
  contains:
    allow_updates:
      description: Whether the WARP client receives update notifications.
      returned: when available
      type: bool
    service_mode_v2:
      description: WARP client service mode configuration.
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
    cloudflare_error_context,
    ensure_settings,
    payload_from_params,
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


def run(module, client):
    account_id = module.params["account_id"]
    payload = payload_from_params(module.params, FIELDS)
    policy = client.zero_trust.devices.policies.default
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the device policy",
        account_id=account_id,
    ):
        current = policy.get(account_id=account_id)

    ensure_settings(
        module,
        "devices_policy",
        "device policy",
        current,
        payload,
        edit=lambda payload: policy.edit(account_id=account_id, **payload),
        context={"account_id": account_id},
    )


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

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
