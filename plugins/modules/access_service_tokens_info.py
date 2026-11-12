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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options: {}
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
    cloudflare_error_context,
    exit_resource_list,
)


def run(module, client):
    account_id = module.params["account_id"]
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Access service tokens",
        account_id=account_id,
    ):
        exit_resource_list(
            module,
            "service_tokens",
            client.zero_trust.access.service_tokens.list(account_id=account_id),
            "Access service token",
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
