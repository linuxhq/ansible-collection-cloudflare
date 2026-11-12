#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: devices_policy_info
short_description: Gather information about the Cloudflare device policy
description:
  - Gather the Cloudflare Zero Trust default device policy for an account.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
"""

EXAMPLES = r"""
- name: Gather device policy
  linuxhq.cloudflare.devices_policy_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
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
        "Cloudflare API request failed while gathering the device policy",
        account_id=account_id,
    ):
        policy = client.zero_trust.devices.policies.default.get(account_id=account_id)

    exit_settings(module, "devices_policy", policy, "device policy")


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
