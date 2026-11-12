#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_apps_info
short_description: Gather information about Cloudflare Access applications
description:
  - Gather Cloudflare Access applications for an account.
  - Results include sensitive values returned by Cloudflare, such as client secrets; protect registered
    results and task output, for example with C(no_log).
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
"""

EXAMPLES = r"""
- name: Gather Access applications
  linuxhq.cloudflare.access_apps_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
access_apps:
  description: Cloudflare Access applications.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Access application identifier.
      returned: always
      type: str
    name:
      description: Access application name.
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
        "Cloudflare API request failed while gathering Access applications",
        account_id=account_id,
    ):
        exit_resource_list(
            module,
            "access_apps",
            client.zero_trust.access.applications.list(account_id=account_id),
            "Access application",
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
