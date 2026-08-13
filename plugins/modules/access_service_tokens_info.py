#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_service_tokens_info
short_description: Gather information about Cloudflare Access service tokens
description:
  - Gather Cloudflare Access service tokens for an account.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
options:
  account_id:
    description:
      - Cloudflare account identifier.
    required: true
    type: str
  api_token:
    description:
      - Cloudflare API token with permissions to read Access service tokens.
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
- name: Gather service token information
  linuxhq.cloudflare.access_service_tokens_info:
    account_id: "{{ access_service_tokens_info_account_id }}"
    api_token: "{{ access_service_tokens_info_api_token }}"
"""

RETURN = r"""
---
service_tokens:
  description: List of Cloudflare Access service tokens.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Service token identifier.
      returned: always
      type: str
    name:
      description: Service token name.
      returned: always
      type: str
    duration:
      description: Configured service token lifetime.
      returned: when available
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
    service_tokens = list_all(
        client,
        cloudflare_path(
            "accounts",
            module.params["account_id"],
            "access",
            "service_tokens",
        ),
    )
    validate_resource_fields(module, service_tokens, ("id", "name"), "Access service token")

    module.exit_json(
        changed=False,
        service_tokens=service_tokens,
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
        list_resources(module, client)


if __name__ == "__main__":
    main()
