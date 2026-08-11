#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_identity_providers_info
short_description: Gather information about Cloudflare Access identity providers
description:
  - Gather Cloudflare Access identity providers for an account.
  - Secret fields such as C(config.client_secret) and C(scim_config.secret) are
    redacted from the results.
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
  contains:
    id:
      description: Identity provider identifier.
      returned: always
      type: str
    name:
      description: Identity provider name.
      returned: always
      type: str
    type:
      description: Identity provider type.
      returned: always
      type: str

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    list_all,
    remove_fields,
    validate_resource_fields,
)


def list_resources(module, client):
    providers = list_all(
        client,
        cloudflare_path(
            "accounts",
            module.params["account_id"],
            "access",
            "identity_providers",
        ),
    )
    validate_resource_fields(
        module, providers, ("id", "type"), "Access identity provider"
    )

    for provider in providers:
        name = provider.get("name")
        if not isinstance(name, str) or name != name.strip():
            module.fail_json(
                msg="Cloudflare API returned malformed Access identity provider data"
            )
        for section, field in (("config", "client_secret"), ("scim_config", "secret")):
            remove_fields(provider.get(section), (field,))

    module.exit_json(changed=False, access_identity_providers=providers)


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
