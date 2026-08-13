#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: zerotrust_connectivity_settings_info
short_description: Gather Cloudflare Zero Trust connectivity settings
description:
  - Gather Cloudflare Zero Trust connectivity settings for an account.
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
- name: Gather Zero Trust connectivity settings
  linuxhq.cloudflare.zerotrust_connectivity_settings_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
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
      description: Whether WARP traffic may use configured off-ramps.
      returned: when available
      type: bool

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    get_result,
    require_mapping,
)


def info(module, client):
    settings = get_result(
        client,
        cloudflare_path(
            "accounts",
            module.params["account_id"],
            "zerotrust",
            "connectivity_settings",
        ),
        default={},
    )
    require_mapping(module, settings, "connectivity settings")

    module.exit_json(changed=False, connectivity_settings=settings)


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
