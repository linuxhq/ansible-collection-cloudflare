#!/usr/bin/python
# Copyright: Ansible Project
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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
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
    cloudflare_error_context,
    exit_resource_list,
)


def run(module, client):
    account_id = module.params["account_id"]
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Rules lists",
        account_id=account_id,
    ):
        exit_resource_list(
            module,
            "rules_lists",
            client.rules.lists.list(account_id=account_id),
            "Rules list",
            required_fields=("id", "name", "kind"),
        )


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
