#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: devices_policy_info
short_description: Gather information about cloudflare devices policy
description:
  - Gather the Cloudflare Zero Trust default device policy for an account.
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
  - cloudflare >= 5.5.0, < 6

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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    get_result,
)


def info(module, client):
    policy = get_result(
        client,
        "/accounts/%s/devices/policy" % module.params["account_id"],
        default={},
    )

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
