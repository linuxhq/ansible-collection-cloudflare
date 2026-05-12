#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_service_tokens_info
short_description: Gather information about cloudflare access service tokens
description:
- Gather Cloudflare Access service tokens for an account.
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
- cloudflare >= 4.3.1, < 5

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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    serialize_resource,
)


def iter_service_tokens(page):
    result = getattr(page, "result", None)
    if result is not None:
        return result

    return page


def list_service_tokens(client, account_id):
    page = client.zero_trust.access.service_tokens.list(
        account_id=account_id,
        per_page=1000,
    )
    return [serialize_resource(item) for item in iter_service_tokens(page)]


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        service_tokens = list_service_tokens(client, module.params["account_id"])

    module.exit_json(
        changed=False,
        service_tokens=service_tokens,
    )


if __name__ == "__main__":
    main()
