#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_groups_info
short_description: Gather information about Cloudflare Access groups
description:
  - Gather Cloudflare Access groups for an account.
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
- name: Gather Access groups
  linuxhq.cloudflare.access_groups_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
access_groups:
  description: Cloudflare Access groups.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Access group identifier.
      returned: always
      type: str
    name:
      description: Access group name.
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
    access_groups = list_all(
        client,
        cloudflare_path("accounts", module.params["account_id"], "access", "groups"),
    )
    validate_resource_fields(module, access_groups, ("id", "name"), "Access group")

    module.exit_json(changed=False, access_groups=access_groups)


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
