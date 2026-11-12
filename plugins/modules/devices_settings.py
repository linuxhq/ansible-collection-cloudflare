#!/usr/bin/python
# Copyright: Ansible Project
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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  disable_for_time:
    type: float
    description:
      - Number of seconds users may temporarily disable the WARP client.
      - When omitted, the current value is left unchanged.
  gateway_proxy_enabled:
    type: bool
    description:
      - Whether the WARP client proxies TCP traffic through Gateway.
      - When omitted, the current value is left unchanged.
  gateway_udp_proxy_enabled:
    type: bool
    description:
      - Whether the WARP client proxies UDP traffic through Gateway.
      - When omitted, the current value is left unchanged.
  root_certificate_installation_enabled:
    type: bool
    description:
      - Whether the WARP client installs the Cloudflare managed root certificate.
      - When omitted, the current value is left unchanged.
  use_zt_virtual_ip:
    type: bool
    description:
      - Whether devices receive a Zero Trust virtual IP address.
      - When omitted, the current value is left unchanged.
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
    cloudflare_error_context,
    ensure_settings,
    payload_from_params,
)

FIELDS = (
    "disable_for_time",
    "gateway_proxy_enabled",
    "gateway_udp_proxy_enabled",
    "root_certificate_installation_enabled",
    "use_zt_virtual_ip",
)


def run(module, client):
    account_id = module.params["account_id"]
    settings = client.zero_trust.devices.settings
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering device settings",
        account_id=account_id,
    ):
        current = settings.get(account_id=account_id)

    ensure_settings(
        module,
        "devices_settings",
        "device settings",
        current,
        payload_from_params(module.params, FIELDS),
        edit=lambda payload: settings.edit(account_id=account_id, **payload),
        context={"account_id": account_id},
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "disable_for_time": {"type": "float"},
            "gateway_proxy_enabled": {"type": "bool"},
            "gateway_udp_proxy_enabled": {"type": "bool"},
            "root_certificate_installation_enabled": {"type": "bool"},
            "use_zt_virtual_ip": {"type": "bool"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
