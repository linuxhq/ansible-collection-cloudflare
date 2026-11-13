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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
  name:
    description:
      - Cloudflare account name to look up.
    required: true
    type: str
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
    type:
      description: Cloudflare account type, such as V(standard) or V(enterprise).
      returned: when the account exists
      type: str
    created_on:
      description: Timestamp when the account was created.
      returned: when provided by Cloudflare
      type: str
    legacy_flags:
      description: Legacy account flags.
      returned: when provided by Cloudflare
      type: dict
    managed_by:
      description: Parent organization details.
      returned: when provided by Cloudflare
      type: dict
    settings:
      description: Account settings.
      returned: when provided by Cloudflare
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    find_resource,
    resource_id,
)


def run(module, client):
    name = module.params["name"]
    with cloudflare_error_context("Cloudflare API request failed while gathering accounts", name=name):
        account = find_resource(module, client.accounts.list(name=name), "account", "name", name)

    if account is not None:
        resource_id(module, account, "account")

    module.exit_json(changed=False, account=account or {})


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
