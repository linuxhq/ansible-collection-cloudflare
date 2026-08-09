#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rules_lists_info
short_description: Gather information about Cloudflare Rules Lists
description:
  - Gather Cloudflare Rules lists for an account.
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
- name: Gather Rules lists
  linuxhq.cloudflare.rules_lists_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
rules_lists:
  description: Cloudflare Rules lists.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Rules list identifier.
      returned: always
      type: str
    name:
      description: Rules list name.
      returned: always
      type: str
    kind:
      description: Data type stored by the Rules list.
      returned: always
      type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    list_all,
    validate_resource_fields,
)


def list_resources(module, client):
    rules_lists = list_all(
        client,
        cloudflare_path("accounts", module.params["account_id"], "rules", "lists"),
        paginate=False,
    )
    validate_resource_fields(module, rules_lists, "id", "Rules list")

    module.exit_json(changed=False, rules_lists=rules_lists)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
