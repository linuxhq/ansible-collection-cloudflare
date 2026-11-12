#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pages_projects_info
short_description: Gather information about Cloudflare Pages projects
description:
  - Gather Cloudflare Pages projects for an account.
  - Results include sensitive values returned by Cloudflare, such as the web analytics
    token; protect registered results and task output, for example with C(no_log).
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
"""

EXAMPLES = r"""
- name: Gather Pages projects
  linuxhq.cloudflare.pages_projects_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
pages_projects:
  description: Cloudflare Pages projects.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Pages project name.
      returned: always
      type: str
    production_branch:
      description: Branch deployed to production.
      returned: when available
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
        "Cloudflare API request failed while gathering Pages projects",
        account_id=account_id,
    ):
        exit_resource_list(
            module,
            "pages_projects",
            client.pages.projects.list(account_id=account_id, per_page=10),
            "Pages project",
            required_fields=("name",),
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
