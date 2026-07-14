#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_identity_providers_info
short_description: Gather information about cloudflare access identity providers
description:
- Gather Cloudflare Access identity providers for an account.
- Secret fields such as C(config.client_secret) and C(scim_config.secret) are
  redacted from the results.
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
- name: Gather Access identity providers
  linuxhq.cloudflare.access_identity_providers_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
access_identity_providers:
  description: Cloudflare Access identity providers.
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
        providers = list_all(
            client,
            "/accounts/%s/access/identity_providers" % module.params["account_id"],
        )

    for provider in providers:
        if not isinstance(provider, dict):
            continue
        for section, field in (("config", "client_secret"), ("scim_config", "secret")):
            if isinstance(provider.get(section), dict):
                provider[section].pop(field, None)

    module.exit_json(changed=False, access_identity_providers=providers)


if __name__ == "__main__":
    main()
