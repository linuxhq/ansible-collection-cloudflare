#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: zerotrust_connectivity_settings
short_description: Manage Cloudflare Zero Trust connectivity settings
description:
  - Manage Cloudflare Zero Trust connectivity settings for an account.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  icmp_proxy_enabled:
    type: bool
    description:
      - Whether Cloudflare proxies ICMP traffic for the account.
      - When omitted, the current value is left unchanged.
  offramp_warp_enabled:
    type: bool
    description:
      - Whether WARP-to-WARP traffic is enabled for the account.
      - When omitted, the current value is left unchanged.
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
  contains:
    icmp_proxy_enabled:
      description: Whether Cloudflare proxies ICMP traffic.
      returned: when available
      type: bool
    offramp_warp_enabled:
      description: Whether WARP-to-WARP traffic is enabled for the account.
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

FIELDS = ("icmp_proxy_enabled", "offramp_warp_enabled")


def run(module, client):
    account_id = module.params["account_id"]
    settings = client.zero_trust.connectivity_settings
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering connectivity settings",
        account_id=account_id,
    ):
        current = settings.get(account_id=account_id)

    ensure_settings(
        module,
        "connectivity_settings",
        "connectivity settings",
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
            "icmp_proxy_enabled": {"type": "bool"},
            "offramp_warp_enabled": {"type": "bool"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
