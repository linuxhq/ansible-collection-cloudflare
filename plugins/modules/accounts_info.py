#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: accounts_info
short_description: Gather information about cloudflare accounts
description:
- Gather Cloudflare account information by name.
author:
- Taylor Kimball (@tkimball83)
options:
  api_token:
    description:
    - Cloudflare API token with permissions to read account settings.
    required: true
    type: str
  name:
    description:
    - Cloudflare account name to look up.
    required: true
    type: str
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Gather account information
  linuxhq.cloudflare.accounts_info:
    api_token: "{{ accounts_info_api_token }}"
    name: "{{ accounts_info_name }}"
"""

RETURN = r"""
---
account:
  description: Cloudflare account information.
  returned: always
  type: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    serialize_resource,
)


def find_account(client, name):
    page = client.accounts.list(
        name=name,
        per_page=1000,
    )
    for account in iter_accounts(page):
        if getattr(account, "name", None) == name:
            return serialize_resource(account)

    return None


def iter_accounts(page):
    result = getattr(page, "result", None)
    if result is not None:
        return result

    return page


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        account = find_account(client, module.params["name"])

    module.exit_json(
        changed=False,
        account=account,
    )


if __name__ == "__main__":
    main()
