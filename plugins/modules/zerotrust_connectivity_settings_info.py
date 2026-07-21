#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: zerotrust_connectivity_settings_info
short_description: Gather information about cloudflare zerotrust connectivity settings
description:
  - Gather Cloudflare Zero Trust connectivity settings for an account.
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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    get_result,
)


def info(module, client):
    settings = get_result(
        client,
        "/accounts/%s/zerotrust/connectivity_settings" % module.params["account_id"],
        default={},
    )

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
