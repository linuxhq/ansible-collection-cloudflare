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
      description: Whether users may update the WARP client.
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
    cloudflare_path,
    get_result,
    require_mapping,
)


def info(module, client):
    policy = get_result(
        client,
        cloudflare_path("accounts", module.params["account_id"], "devices", "policy"),
        default={},
    )
    require_mapping(module, policy, "device policy")

    module.exit_json(changed=False, devices_policy=policy)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        info(module, client)


if __name__ == "__main__":
    main()
