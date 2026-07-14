#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pages_projects_info
short_description: Gather information about cloudflare pages projects
description:
- Gather Cloudflare Pages projects for an account.
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
- cloudflare >= 4.3.1, < 5

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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    list_all,
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
        projects = list_all(
            client,
            "/accounts/%s/pages/projects" % module.params["account_id"],
            paginate=False,
        )

    module.exit_json(changed=False, pages_projects=projects)


if __name__ == "__main__":
    main()
