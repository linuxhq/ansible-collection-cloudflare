#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: devices_settings_info
short_description: Gather information about Cloudflare device settings
description:
  - Gather account-wide Cloudflare Zero Trust device settings.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
"""

EXAMPLES = r"""
- name: Gather device settings
  linuxhq.cloudflare.devices_settings_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    exit_settings,
)


def run(module, client):
    account_id = module.params["account_id"]
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering device settings",
        account_id=account_id,
    ):
        settings = client.zero_trust.devices.settings.get(account_id=account_id)

    exit_settings(module, "devices_settings", settings, "device settings")


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
