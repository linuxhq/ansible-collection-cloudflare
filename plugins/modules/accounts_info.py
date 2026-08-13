#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: accounts_info
short_description: Gather information about Cloudflare accounts
description:
  - Gather Cloudflare account information by name.
version_added: '2.0.0'
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
  contains:
    id:
      description: Cloudflare account identifier.
      returned: when the account exists
      type: str
    name:
      description: Cloudflare account name.
      returned: when the account exists
      type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    resource_field,
    resource_id,
    serialize_resource,
)


def info(module, client):
    account = {}

    with cloudflare_error_context(
        "Cloudflare API request failed while gathering accounts",
        name=module.params["name"],
    ):
        for account_info in client.accounts.list(name=module.params["name"]):
            account_info = serialize_resource(account_info)
            account_name = resource_field(module, account_info, "name", "account")
            resource_id(module, account_info, "account")
            if account_name == module.params["name"]:
                account = account_info
                break

    module.exit_json(
        changed=False,
        account=account,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        info(module, client)


if __name__ == "__main__":
    main()
